from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from agent_core import CapabilityStatus, NotFoundError, PageRequest
from agent_data import UnitOfWork

from ...dependencies import get_knowledge_client, get_uow
from ...knowledge import KnowledgeClient
from ...responses import ApiEnvelope, PageData, envelope, page_payload
from ...security import CurrentUser, get_current_user, require_admin
from .schemas import (
    CapabilityNoteResponse,
    CapabilityStatusUpdate,
    CapabilitySyncDocumentResponse,
    CapabilitySyncRequest,
    CapabilitySyncResponse,
)
from .service import sync_capability_to_knowledge, update_capability_status

router = APIRouter(
    prefix="/api/capabilities",
    tags=["capabilities"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=ApiEnvelope[PageData[CapabilityNoteResponse]])
def list_capabilities(
    project_id: UUID,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    status: CapabilityStatus | None = None,
    topic: str | None = None,
    tags: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    if uow.projects.get(project_id) is None:
        raise NotFoundError("项目不存在")
    page = uow.capabilities.list_by_project(
        project_id,
        PageRequest(limit=limit, offset=offset),
        status=status,
        topic=topic,
        tags=tuple(tags or ()),
    )
    return envelope(page_payload(page.records, page.total))


@router.get("/search", response_model=ApiEnvelope[PageData[CapabilityNoteResponse]])
def search_capabilities(
    project_id: UUID,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    topic: str | None = None,
    tags: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    if uow.projects.get(project_id) is None:
        raise NotFoundError("项目不存在")
    page = uow.capabilities.list_by_project(
        project_id,
        PageRequest(limit=limit, offset=offset),
        status=CapabilityStatus.CONFIRMED,
        topic=topic,
        tags=tuple(tags or ()),
    )
    return envelope(page_payload(page.records, page.total))


@router.patch("/{note_id}", response_model=ApiEnvelope[CapabilityNoteResponse])
def change_status(
    note_id: UUID,
    body: CapabilityStatusUpdate,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict[str, object]:
    note = uow.capabilities.get(note_id)
    if note is None or note.project_id != body.project_id:
        raise NotFoundError("能力条目不存在或不属于当前项目")
    updated = update_capability_status(
        uow,
        note=note,
        status=body.status,
        actor=user.username,
    )
    return envelope(updated, message="updated")


@router.post("/{note_id}/sync", response_model=ApiEnvelope[CapabilitySyncResponse])
def sync_capability(
    note_id: UUID,
    body: CapabilitySyncRequest,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    knowledge: Annotated[KnowledgeClient, Depends(get_knowledge_client)],
    user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict[str, object]:
    note = uow.capabilities.get(note_id)
    if note is None or note.project_id != body.project_id:
        raise NotFoundError("能力条目不存在或不属于当前项目")
    project = uow.projects.get(body.project_id)
    if project is None:
        raise NotFoundError("项目不存在")
    result = sync_capability_to_knowledge(
        uow,
        knowledge,
        project=project,
        note=note,
        actor=user.username,
    )
    response = CapabilitySyncResponse(
        note=CapabilityNoteResponse.model_validate(note),
        document=CapabilitySyncDocumentResponse.model_validate(result.document),
        deduplicated=result.deduplicated,
    )
    return envelope(
        response,
        message="skipped" if result.deduplicated else "created",
    )
