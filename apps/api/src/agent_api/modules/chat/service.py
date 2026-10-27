from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from agent_core import (
    AuditLog,
    Citation,
    ConflictError,
    Conversation,
    Message,
    MessageRole,
    NotFoundError,
    Project,
    ToolCallSummary,
    utc_now,
)
from agent_data import UnitOfWork

from .schemas import CitationResponse, MessageResponse, ToolCallResponse


def resolve_project(
    uow: UnitOfWork,
    *,
    body_project_id: UUID | None,
    header_project_id: str | None,
    model: str,
) -> Project | None:
    project_id = body_project_id
    if project_id is None and header_project_id:
        try:
            project_id = UUID(header_project_id)
        except ValueError as exc:
            raise NotFoundError("X-Project-Id 不是有效的项目标识") from exc
    if project_id is None and model.startswith("project-"):
        try:
            project_id = UUID(model.removeprefix("project-"))
        except ValueError as exc:
            raise NotFoundError("模型标识中没有有效的项目信息") from exc
    if project_id is None:
        return None
    project = uow.projects.get(project_id)
    if project is None:
        raise NotFoundError("项目不存在")
    if not project.enabled:
        raise ConflictError("项目已停用")
    return project


def get_or_create_conversation(
    uow: UnitOfWork,
    *,
    project: Project,
    conversation_id: UUID | None,
    external_id: str | None,
    first_message: str,
) -> Conversation:
    conversation: Conversation | None = None
    if conversation_id is not None:
        conversation = uow.conversations.get(conversation_id)
        if conversation is None or conversation.project_id != project.id:
            raise NotFoundError("会话不存在或不属于当前项目")
    if conversation is None and external_id:
        conversation = uow.conversations.find_by_external_id(external_id)
        if conversation is not None and conversation.project_id != project.id:
            raise ConflictError("外部会话标识已被其他项目占用")

    now = utc_now()
    if conversation is None:
        return uow.conversations.add(
            Conversation(
                id=uuid4(),
                project_id=project.id,
                agent_id=None,
                title=_title_from(first_message),
                external_id=external_id,
                created_at=now,
                updated_at=now,
            )
        )

    if conversation.external_id is None and external_id:
        conversation = replace(conversation, external_id=external_id, updated_at=now)
        return uow.conversations.update(conversation)
    return conversation


def add_message(
    uow: UnitOfWork,
    *,
    conversation_id: UUID,
    role: MessageRole,
    content: str,
    tool_calls: tuple[ToolCallSummary, ...] = (),
    citations: tuple[Citation, ...] = (),
) -> Message:
    now = utc_now()
    return uow.messages.add(
        Message(
            id=uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            citations=citations,
            created_at=now,
            updated_at=now,
        )
    )


def touch_conversation(uow: UnitOfWork, conversation: Conversation) -> Conversation:
    return uow.conversations.update(replace(conversation, updated_at=utc_now()))


def record_tool_audits(
    uow: UnitOfWork,
    *,
    actor: str,
    project_id: UUID,
    conversation_id: UUID,
    tool_calls: tuple[ToolCallSummary, ...],
) -> None:
    now = utc_now()
    for tool_call in tool_calls:
        uow.audit_logs.add(
            AuditLog(
                id=uuid4(),
                actor=actor,
                action="chat.tool_call",
                resource_type="conversation",
                resource_id=str(conversation_id),
                project_id=project_id,
                detail={
                    "tool": tool_call.name,
                    "success": tool_call.success,
                    "error": tool_call.error,
                    "arguments": dict(tool_call.arguments),
                },
                created_at=now,
                updated_at=now,
            )
        )


def message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        tool_calls=[
            ToolCallResponse(
                name=item.name,
                success=item.success,
                arguments=dict(item.arguments),
                error=item.error,
                duration_ms=item.duration_ms,
            )
            for item in message.tool_calls
        ],
        citations=[
            CitationResponse(
                document_id=item.document_id,
                document_title=item.document_title,
                heading_path=list(item.heading_path),
                snippet=item.snippet,
                score=item.score,
                page=item.page,
            )
            for item in message.citations
        ],
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def _title_from(text: str) -> str:
    normalized = " ".join(text.split())
    return (normalized[:80] or "新会话").strip()
