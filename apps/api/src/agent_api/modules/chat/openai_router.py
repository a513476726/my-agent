from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID, uuid4

from agentscope.model import ChatModelBase
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse

from agent_core import (
    Citation,
    DomainError,
    Message,
    MessageRole,
    PageRequest,
    Project,
    ToolCallSummary,
    utc_now,
)
from agent_data import UnitOfWork
from agent_runtime.code_access import LocalCodeAccess
from agent_runtime.runtime import build_agent, stream_agent_reply

from ...config import Settings, get_settings
from ...dependencies import (
    get_chat_model_or_none,
    get_code_access,
    get_knowledge_client,
    get_uow,
)
from ...knowledge import KnowledgeClient
from ...security import CurrentUser, get_api_caller
from .openai_schemas import ChatCompletionRequest
from .service import (
    add_message,
    get_or_create_conversation,
    record_tool_audits,
    resolve_project,
    touch_conversation,
)

router = APIRouter(
    prefix="/v1",
    tags=["openai"],
    dependencies=[Depends(get_api_caller)],
)

_NO_PROJECT_MESSAGE = (
    "请先选择项目后再提问。项目标识可通过 project_id、X-Project-Id 或 project-<uuid> 模型指定。"
)


@router.get("/models")
def list_models(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    projects = uow.projects.list(PageRequest(limit=200, offset=0), enabled=True)
    data: list[dict[str, object]] = [
        {
            "id": settings.agent_model,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "volcengine",
        }
    ]
    for project in projects.records:
        data.append(
            {
                "id": f"project-{project.id}",
                "object": "model",
                "created": int(project.created_at.timestamp()),
                "owned_by": "my-agent",
                "name": project.name,
            }
        )
    return {"object": "list", "data": data}


@router.post("/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    knowledge: Annotated[KnowledgeClient, Depends(get_knowledge_client)],
    model: Annotated[ChatModelBase | None, Depends(get_chat_model_or_none)],
    code: Annotated[LocalCodeAccess, Depends(get_code_access)],
    settings: Annotated[Settings, Depends(get_settings)],
    caller: Annotated[CurrentUser, Depends(get_api_caller)],
    header_project_id: Annotated[str | None, Header(alias="X-Project-Id")] = None,
    header_conversation_id: Annotated[str | None, Header(alias="X-Conversation-Id")] = None,
) -> object:
    text = body.last_user_text()
    if not text:
        return _openai_error(400, "最后一条用户消息不能为空", "invalid_request_error")

    try:
        project = resolve_project(
            uow,
            body_project_id=body.project_id,
            header_project_id=header_project_id,
            model=body.model,
        )
    except DomainError as exc:
        return _openai_error(404, exc.message, "invalid_request_error")

    if project is None:
        if body.stream:
            return _no_project_stream(body)
        return JSONResponse(_completion_payload(body, _NO_PROJECT_MESSAGE))

    if model is None:
        return _openai_error(503, "未配置模型密钥 ARK_API_KEY", "service_unavailable")

    external_id = body.external_conversation_id or header_conversation_id
    try:
        conversation = get_or_create_conversation(
            uow,
            project=project,
            conversation_id=body.conversation_id,
            external_id=external_id,
            first_message=text,
        )
        history = _request_history(body) or uow.messages.list_by_conversation(conversation.id)
        add_message(
            uow,
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=text,
        )
        touch_conversation(uow, conversation)
        uow.commit()
    except DomainError as exc:
        return _openai_error(409, exc.message, "invalid_request_error")

    agent = build_agent(
        model=model,
        project=project,
        knowledge=knowledge,
        code=code,
        max_iters=settings.agent_max_iters,
    )
    if body.stream:
        return StreamingResponse(
            _stream_completion(
                agent=agent,
                body=body,
                text=text,
                history=history,
                project=project,
                conversation_id=conversation.id,
                actor=caller.username,
                uow=uow,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return await _complete(
        agent=agent,
        body=body,
        text=text,
        history=history,
        project=project,
        conversation_id=conversation.id,
        actor=caller.username,
        uow=uow,
    )


async def _complete(
    *,
    agent: object,
    body: ChatCompletionRequest,
    text: str,
    history: object,
    project: Project,
    conversation_id: UUID,
    actor: str,
    uow: UnitOfWork,
) -> object:
    try:
        result = None
        async for update in stream_agent_reply(
            agent=agent,  # type: ignore[arg-type]
            text=text,
            history=history,  # type: ignore[arg-type]
        ):
            if update.result is not None:
                result = update.result
        if result is None:
            return _openai_error(502, "模型未返回结果", "upstream_error")
        if result.error:
            return _openai_error(502, result.error, "upstream_error")
    except Exception as exc:
        return _openai_error(502, f"智能体执行失败: {exc}", "upstream_error")

    content = _decorated_content(result.content, result.citations, result.tool_calls)
    _persist_assistant(
        uow,
        conversation_id=conversation_id,
        project=project,
        actor=actor,
        content=content,
        citations=result.citations,
        tool_calls=result.tool_calls,
    )
    return JSONResponse(
        _completion_payload(
            body,
            content,
            citations=result.citations,
            tool_calls=result.tool_calls,
        )
    )


async def _stream_completion(
    *,
    agent: object,
    body: ChatCompletionRequest,
    text: str,
    history: object,
    project: Project,
    conversation_id: UUID,
    actor: str,
    uow: UnitOfWork,
) -> AsyncIterator[str]:
    completion_id = f"chatcmpl-{uuid4().hex}"
    created = int(time.time())
    yield _sse(
        {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": body.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None,
                }
            ],
        }
    )

    streamed: list[str] = []
    try:
        result = None
        async for update in stream_agent_reply(
            agent=agent,  # type: ignore[arg-type]
            text=text,
            history=history,  # type: ignore[arg-type]
        ):
            if update.delta:
                streamed.append(update.delta)
                yield _sse(
                    {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": body.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": update.delta},
                                "finish_reason": None,
                            }
                        ],
                    }
                )
            if update.result is not None:
                result = update.result
        if result is None:
            yield _sse({"error": {"message": "模型未返回结果", "type": "upstream_error"}})
            yield "data: [DONE]\n\n"
            return
        if result.error:
            yield _sse({"error": {"message": result.error, "type": "upstream_error"}})
            yield "data: [DONE]\n\n"
            return

        full_content = _decorated_content(result.content, result.citations, result.tool_calls)
        streamed_text = "".join(streamed)
        suffix = _suffix_after(streamed_text, full_content)
        if suffix:
            yield _sse(
                {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": body.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": suffix},
                            "finish_reason": None,
                        }
                    ],
                }
            )
        _persist_assistant(
            uow,
            conversation_id=conversation_id,
            project=project,
            actor=actor,
            content=full_content,
            citations=result.citations,
            tool_calls=result.tool_calls,
        )
        yield _sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": body.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "citations": _citations_payload(result.citations),
                "tool_calls": _tool_calls_payload(result.tool_calls),
            }
        )
    except Exception as exc:
        yield _sse({"error": {"message": f"智能体执行失败: {exc}", "type": "upstream_error"}})
    yield "data: [DONE]\n\n"


def _persist_assistant(
    uow: UnitOfWork,
    *,
    conversation_id: UUID,
    project: Project,
    actor: str,
    content: str,
    citations: tuple[Citation, ...],
    tool_calls: tuple[ToolCallSummary, ...],
) -> None:
    add_message(
        uow,
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content=content,
        citations=citations,
        tool_calls=tool_calls,
    )
    record_tool_audits(
        uow,
        actor=actor,
        project_id=project.id,
        conversation_id=conversation_id,
        tool_calls=tool_calls,
    )
    conversation = uow.conversations.get(conversation_id)
    if conversation is not None:
        touch_conversation(uow, conversation)
    uow.commit()


def _decorated_content(
    content: str,
    citations: tuple[Citation, ...],
    tool_calls: tuple[ToolCallSummary, ...],
) -> str:
    normalized = content.strip()
    failed = [item for item in tool_calls if not item.success]
    if failed:
        details = "\n".join(f"- {item.name}: {item.error or '工具执行失败'}" for item in failed)
        normalized = f"{normalized}\n\n工具调用失败：\n{details}".strip()
    if citations and "参考来源" not in normalized:
        sources = []
        for index, citation in enumerate(citations, start=1):
            heading = " / ".join(citation.heading_path) or "正文"
            sources.append(f"{index}. {citation.document_title} · {heading}\n   {citation.snippet}")
        normalized = f"{normalized}\n\n参考来源：\n" + "\n".join(sources)
    return normalized or "模型未返回文本内容。"


def _suffix_after(streamed: str, full: str) -> str:
    if not streamed:
        return full
    if full.startswith(streamed):
        return full[len(streamed) :]
    if streamed.startswith(full):
        return ""
    return full


def _completion_payload(
    body: ChatCompletionRequest,
    content: str,
    *,
    citations: tuple[Citation, ...] = (),
    tool_calls: tuple[ToolCallSummary, ...] = (),
) -> dict[str, object]:
    return {
        "id": f"chatcmpl-{uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "citations": _citations_payload(citations),
        "tool_calls": _tool_calls_payload(tool_calls),
    }


def _no_project_stream(body: ChatCompletionRequest) -> StreamingResponse:
    completion_id = f"chatcmpl-{uuid4().hex}"
    created = int(time.time())

    async def generate() -> AsyncIterator[str]:
        yield _sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": body.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": _NO_PROJECT_MESSAGE},
                        "finish_reason": None,
                    }
                ],
            }
        )
        yield _sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": body.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "citations": [],
                "tool_calls": [],
            }
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


def _openai_error(status_code: int, message: str, error_type: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": error_type}},
    )


def _citations_payload(citations: tuple[Citation, ...]) -> list[dict[str, object]]:
    return [
        {
            "document_id": str(item.document_id),
            "document_title": item.document_title,
            "heading_path": list(item.heading_path),
            "snippet": item.snippet,
            "score": item.score,
            "page": item.page,
        }
        for item in citations
    ]


def _tool_calls_payload(
    tool_calls: tuple[ToolCallSummary, ...],
) -> list[dict[str, object]]:
    return [
        {
            "name": item.name,
            "success": item.success,
            "arguments": dict(item.arguments),
            "error": item.error,
            "duration_ms": item.duration_ms,
        }
        for item in tool_calls
    ]


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _request_history(body: ChatCompletionRequest) -> tuple[Message, ...]:
    last_user_index = -1
    for index, message in enumerate(body.messages):
        if message.role == "user":
            last_user_index = index
    if last_user_index <= 0:
        return ()
    now = utc_now()
    history: list[Message] = []
    for message in body.messages[:last_user_index]:
        if message.role not in {"user", "assistant"}:
            continue
        text = message.text().strip()
        if not text:
            continue
        history.append(
            Message(
                id=uuid4(),
                conversation_id=uuid4(),
                role=MessageRole(message.role),
                content=text,
                created_at=now,
                updated_at=now,
            )
        )
    return tuple(history)
