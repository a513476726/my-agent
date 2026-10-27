from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from agent_core import PageRequest
from agent_data import UnitOfWork

from ...dependencies import get_uow
from ...responses import ApiEnvelope, PageData, envelope, page_payload
from ...security import CurrentUser, get_current_user, require_admin
from .schemas import AuditLogResponse, MenuItem, UserInfoResponse

router = APIRouter(prefix="/admin", tags=["admin"])

MENU = [
    {"name": "dashboard", "path": "/", "meta": {"title": "工作台"}},
    {
        "name": "project-space",
        "path": "project-space",
        "meta": {"title": "项目空间"},
        "children": [
            {"name": "projects", "path": "projects", "meta": {"title": "项目管理"}},
            {"name": "documents", "path": "documents", "meta": {"title": "文档管理"}},
            {"name": "reports", "path": "reports", "meta": {"title": "报告"}},
        ],
    },
    {
        "name": "operations",
        "path": "operations",
        "meta": {"title": "运营管理"},
        "children": [
            {"name": "capabilities", "path": "capabilities", "meta": {"title": "能力沉淀"}},
            {"name": "jobs", "path": "jobs", "meta": {"title": "任务"}},
            {"name": "audit", "path": "audit", "meta": {"title": "审计日志"}},
        ],
    },
]


@router.get("/user/info", response_model=ApiEnvelope[UserInfoResponse])
def user_info(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    return envelope(
        {
            "username": user.username,
            "nickname": user.username,
            "roles": [user.role],
        }
    )


@router.get("/menu/userMenu/{app}", response_model=ApiEnvelope[list[MenuItem]])
def user_menu(
    app: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    if app != "admin":
        raise HTTPException(status_code=404, detail="未知应用")
    return envelope(MENU)


@router.get(
    "/audit-logs",
    response_model=ApiEnvelope[PageData[AuditLogResponse]],
)
def list_audit_logs(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[CurrentUser, Depends(require_admin)],
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    project_id: UUID | None = None,
) -> dict[str, object]:
    page = uow.audit_logs.list(PageRequest(limit=limit, offset=offset), project_id=project_id)
    return envelope(page_payload(page.records, page.total))
