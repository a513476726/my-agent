from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from agent_core import NotFoundError, PageRequest
from agent_data import UnitOfWork

from ...dependencies import get_uow
from ...responses import ApiEnvelope, PageData, envelope, page_payload
from ...security import get_current_user
from .schemas import ConversationResponse, MessageResponse
from .service import message_response

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/conversations", response_model=ApiEnvelope[PageData[ConversationResponse]])
def list_conversations(
    project_id: UUID,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    if uow.projects.get(project_id) is None:
        raise NotFoundError("项目不存在")
    page = uow.conversations.list_by_project(project_id, PageRequest(limit=limit, offset=offset))
    return envelope(page_payload(page.records, page.total))


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ApiEnvelope[list[MessageResponse]],
)
def list_messages(
    conversation_id: UUID,
    project_id: UUID,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> dict[str, object]:
    conversation = uow.conversations.get(conversation_id)
    if conversation is None or conversation.project_id != project_id:
        raise NotFoundError("会话不存在或不属于当前项目")
    messages = uow.messages.list_by_conversation(conversation_id)
    return envelope([message_response(message) for message in messages])
