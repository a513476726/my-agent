from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from agent_core import (
    DomainValidationError,
    NotFoundError,
    PageRequest,
    ReportKind,
    TimeRange,
)
from agent_data import UnitOfWork

from ...dependencies import get_uow
from ...responses import ApiEnvelope, PageData, envelope, page_payload
from ...security import get_current_user
from .schemas import ReportDetailResponse, ReportItemResponse, ReportResponse

router = APIRouter(
    prefix="/api/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=ApiEnvelope[PageData[ReportResponse]])
def list_reports(
    project_id: UUID,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    kind: ReportKind | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    if uow.projects.get(project_id) is None:
        raise NotFoundError("项目不存在")
    period = None
    if period_start is not None or period_end is not None:
        if period_start is None or period_end is None:
            raise DomainValidationError("period_start 与 period_end 必须同时提供")
        period = TimeRange(start=period_start, end=period_end)
    page = uow.reports.list_by_project(
        project_id,
        PageRequest(limit=limit, offset=offset),
        kind=kind,
        period=period,
    )
    return envelope(page_payload(page.records, page.total))


@router.get("/{report_id}", response_model=ApiEnvelope[ReportDetailResponse])
def get_report(
    report_id: UUID,
    project_id: UUID,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> dict[str, object]:
    report = uow.reports.get(report_id)
    if report is None or report.project_id != project_id:
        raise NotFoundError("报告不存在或不属于当前项目")
    items = uow.report_items.list_by_report(report.id)
    detail = ReportDetailResponse(
        **ReportResponse.model_validate(report).model_dump(),
        items=[ReportItemResponse.model_validate(item) for item in items],
    )
    return envelope(detail)


@router.get("/{report_id}/export")
def export_report(
    report_id: UUID,
    project_id: UUID,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> PlainTextResponse:
    report = uow.reports.get(report_id)
    if report is None or report.project_id != project_id:
        raise NotFoundError("报告不存在或不属于当前项目")
    return PlainTextResponse(
        content=report.body,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.md"'},
    )
