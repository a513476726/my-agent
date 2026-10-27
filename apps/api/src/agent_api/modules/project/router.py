from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError

from agent_core import AuditLog, ConflictError, PageRequest, Project, utc_now
from agent_data import UnitOfWork

from ...dependencies import get_uow
from ...responses import ApiEnvelope, PageData, envelope, page_payload
from ...security import CurrentUser, get_current_user, require_admin
from .schemas import ProjectCreate, ProjectResponse

router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=ApiEnvelope[PageData[ProjectResponse]])
def list_projects(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    enabled: bool | None = None,
) -> dict[str, object]:
    page = uow.projects.list(PageRequest(limit=limit, offset=offset), enabled=enabled)
    return envelope(page_payload(page.records, page.total))


@router.post("", response_model=ApiEnvelope[ProjectResponse])
def create_project(
    body: ProjectCreate,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict[str, object]:
    if uow.projects.get_by_path(body.path) is not None:
        raise ConflictError("项目路径已存在")

    now = utc_now()
    project = Project(
        id=uuid4(),
        name=body.name,
        path=body.path,
        vcs_type=body.vcs_type,
        enabled=body.enabled,
        created_at=now,
        updated_at=now,
    )
    try:
        created = uow.projects.add(project)
    except IntegrityError as exc:
        raise ConflictError("项目路径已存在") from exc

    uow.audit_logs.add(
        AuditLog(
            id=uuid4(),
            actor=user.username,
            action="project.create",
            resource_type="project",
            resource_id=str(created.id),
            project_id=created.id,
            detail={"name": created.name, "path": created.path},
            created_at=now,
            updated_at=now,
        )
    )
    return envelope(created, message="created")
