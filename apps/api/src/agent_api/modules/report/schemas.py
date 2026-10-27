from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from agent_core import ReportKind, ReportStatus


class ReportPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start: datetime
    end: datetime


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    job_run_id: UUID | None
    kind: ReportKind
    period: ReportPeriodResponse
    title: str
    body: str
    status: ReportStatus
    created_at: datetime
    updated_at: datetime


class CommitRangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_commit: str
    end_commit: str


class ReportItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_id: UUID
    project_id: UUID
    title: str
    summary: str
    category: str
    commit_range: CommitRangeResponse
    created_at: datetime
    updated_at: datetime


class ReportDetailResponse(ReportResponse):
    items: list[ReportItemResponse]
