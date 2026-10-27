from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from agent_core import ConflictError, NotFoundError, PageRequest
from agent_data import UnitOfWork

from ...dependencies import get_knowledge_client, get_uow
from ...knowledge import KnowledgeClient
from ...responses import ApiEnvelope, PageData, envelope, page_payload
from ...security import CurrentUser, get_current_user, require_admin
from .schemas import DocumentIngestResponse, DocumentResponse
from .service import ingest_document

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=ApiEnvelope[PageData[DocumentResponse]])
def list_documents(
    project_id: UUID,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    if uow.projects.get(project_id) is None:
        raise NotFoundError("项目不存在")
    page = uow.documents.list_by_project(project_id, PageRequest(limit=limit, offset=offset))
    return envelope(page_payload(page.records, page.total))


@router.post("/ingest", response_model=ApiEnvelope[DocumentIngestResponse])
def ingest(
    project_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    knowledge: Annotated[KnowledgeClient, Depends(get_knowledge_client)],
    user: Annotated[CurrentUser, Depends(require_admin)],
    source_path: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    project = uow.projects.get(project_id)
    if project is None:
        raise NotFoundError("项目不存在")
    if not project.enabled:
        raise ConflictError("项目已停用")
    document, deduplicated = ingest_document(
        uow=uow,
        knowledge=knowledge,
        project=project,
        actor=user.username,
        filename=file.filename or "",
        source_path=source_path,
        content=file.file.read(),
        content_type=file.content_type,
    )
    response = DocumentIngestResponse(
        **DocumentResponse.model_validate(document).model_dump(),
        deduplicated=deduplicated,
    )
    return envelope(response, message="skipped" if deduplicated else "created")
