from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from uuid import UUID

from agentscope.agent import Agent, InjectionConfig, ReActConfig
from agentscope.credential import VolcengineCredential
from agentscope.event import (
    ReplyEndEvent,
    TextBlockDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallStartEvent,
    ToolResultEndEvent,
    ToolResultTextDeltaEvent,
)
from agentscope.message import AssistantMsg, Msg, ToolResultState, UserMsg
from agentscope.model import ChatModelBase, VolcengineChatModel
from agentscope.tool import Toolkit

from agent_core import (
    Citation,
    CodeAccess,
    KnowledgeGateway,
    Message,
    MessageRole,
    Project,
    ToolCallSummary,
)

from .tools import ProjectToolbox, ToolContext

DEFAULT_SYSTEM_PROMPT = """你是个人工作助理，负责结合项目文档与代码回答研发问题。

工作规则：
1. 先检索知识库确认需求，再读取代码确认实现；引用知识库时必须保留文档标题与章节路径。
2. 只能访问当前绑定项目；不得猜测其他项目的内容，也不得请求项目外路径。
3. 工具失败时必须如实说明失败原因，不能把失败描述成成功或编造结果。
4. 回答简洁、给出文件路径与行号，明确区分“文档规定”和“代码现状”。
5. 如果上下文不足以回答，直接说明缺少什么，不要臆测。"""


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    content: str
    tool_calls: tuple[ToolCallSummary, ...] = ()
    citations: tuple[Citation, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AgentUpdate:
    delta: str | None = None
    result: AgentRunResult | None = None


@dataclass(slots=True)
class _PendingTool:
    name: str
    started_at: float
    arguments_json: str = ""
    output: str = ""
    success: bool = True
    error: str | None = None
    citations: list[Citation] = field(default_factory=list)


def build_volcengine_model(
    *,
    api_key: str,
    model: str,
    base_url: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> VolcengineChatModel:
    parameters = VolcengineChatModel.Parameters(
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return VolcengineChatModel(
        credential=VolcengineCredential(api_key=api_key, base_url=base_url),
        model=model,
        parameters=parameters,
        stream=True,
    )


def build_agent(
    *,
    model: ChatModelBase,
    project: Project | None,
    knowledge: KnowledgeGateway | None,
    code: CodeAccess,
    max_iters: int = 8,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> Agent:
    tools = ()
    if project is not None:
        tools = ProjectToolbox(
            ToolContext(project=project, knowledge=knowledge, code=code)
        ).build_tools()
    system = _system_prompt(system_prompt, project)
    return Agent(
        name="work-assistant",
        system_prompt=system,
        model=model,
        toolkit=Toolkit(tools=list(tools)),
        react_config=ReActConfig(max_iters=max_iters),
        injection_config=InjectionConfig(timezone="Asia/Shanghai"),
    )


async def stream_agent_reply(
    *,
    agent: Agent,
    text: str,
    history: tuple[Message, ...] = (),
) -> AsyncIterator[AgentUpdate]:
    pending: dict[str, _PendingTool] = {}
    citations: list[Citation] = []
    final_msg: Msg | None = None
    reply_error: str | None = None
    emitted_text = False

    inputs: list[Msg] = [
        AssistantMsg(name="work-assistant", content=message.content)
        if message.role is MessageRole.ASSISTANT
        else UserMsg(name="user", content=message.content)
        for message in history
        if message.role in (MessageRole.USER, MessageRole.ASSISTANT) and message.content
    ]
    inputs.append(UserMsg(name="user", content=text))

    async for item in agent.reply_stream(
        inputs,
        yield_final_msg=True,
    ):
        if isinstance(item, TextBlockDeltaEvent):
            if item.delta:
                emitted_text = True
                yield AgentUpdate(delta=item.delta)
        elif isinstance(item, ToolCallStartEvent):
            pending[item.tool_call_id] = _PendingTool(
                name=item.tool_call_name,
                started_at=time.monotonic(),
            )
        elif isinstance(item, ToolCallDeltaEvent):
            tool = pending.get(item.tool_call_id)
            if tool is not None:
                tool.arguments_json += item.delta
        elif isinstance(item, ToolResultTextDeltaEvent):
            tool = pending.get(item.tool_call_id)
            if tool is not None:
                tool.output += item.delta
        elif isinstance(item, ToolResultEndEvent):
            tool = pending.get(item.tool_call_id)
            if tool is not None:
                state = ToolResultState(item.state)
                tool.success = state == ToolResultState.SUCCESS
                if not tool.success:
                    tool.error = tool.output.strip() or str(
                        item.metadata.get("error", "工具执行失败")
                    )
                tool.citations = _citations_from_metadata(item.metadata)
                citations.extend(tool.citations)
        elif isinstance(item, ReplyEndEvent):
            if item.error is not None:
                reply_error = item.error.message
        elif isinstance(item, Msg) and item.role == "assistant":
            final_msg = item

    content = final_msg.get_text_content() if final_msg is not None else None
    content = content or ""
    if content and not emitted_text:
        yield AgentUpdate(delta=content)

    summaries = tuple(
        ToolCallSummary(
            name=tool.name,
            success=tool.success,
            arguments=_parse_arguments(tool.arguments_json),
            error=_normalize_error(tool.error),
            duration_ms=int((time.monotonic() - tool.started_at) * 1000),
        )
        for tool in pending.values()
    )
    yield AgentUpdate(
        result=AgentRunResult(
            content=content,
            tool_calls=summaries,
            citations=_deduplicate_citations(citations),
            error=reply_error,
        )
    )


def _system_prompt(base: str, project: Project | None) -> str:
    if project is None:
        return f"{base}\n\n当前未绑定项目：不得调用任何工具，只提示用户先选择项目后再提问。"
    return (
        f"{base}\n\n当前项目：{project.name}\n"
        f"项目根目录：{project.path}\n"
        "本次会话中的所有知识检索、文件读取与 Git 查询都只能针对该项目。"
    )


def _parse_arguments(value: str) -> tuple[tuple[str, object], ...]:
    if not value.strip():
        return ()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return ()
    if not isinstance(parsed, dict):
        return ()
    return tuple((str(key), item) for key, item in parsed.items())


def _normalize_error(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or "工具执行失败"


def _citations_from_metadata(metadata: dict[str, object]) -> list[Citation]:
    raw = metadata.get("citations")
    if not isinstance(raw, list):
        return []
    citations: list[Citation] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            heading_path = item.get("heading_path") or []
            citations.append(
                Citation(
                    document_id=UUID(str(item["document_id"])),
                    document_title=str(item["document_title"]),
                    heading_path=tuple(str(value) for value in heading_path),
                    snippet=str(item["snippet"]),
                    score=float(item["score"]) if item.get("score") is not None else None,
                    page=int(item["page"]) if item.get("page") is not None else None,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return citations


def _deduplicate_citations(citations: list[Citation]) -> tuple[Citation, ...]:
    seen: set[tuple[object, ...]] = set()
    result: list[Citation] = []
    for citation in citations:
        key = (
            citation.document_id,
            citation.heading_path,
            citation.snippet,
            citation.page,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(citation)
    return tuple(result)
