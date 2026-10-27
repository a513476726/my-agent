from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from agent_core import JobKind, JobRunStatus, TriggerType


class JobTriggerRequest(BaseModel):
    project_id: UUID | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: JobKind
    cron: str
    enabled: bool
    config: list[tuple[str, object]]
    created_at: datetime
    updated_at: datetime


class JobRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    project_id: UUID
    run_key: str
    status: JobRunStatus
    trigger: TriggerType
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    report_id: UUID | None
    created_at: datetime
    updated_at: datetime
