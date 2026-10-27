from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from agent_core import NotFoundError, PageRequest, utc_now
from agent_data import UnitOfWork

from ...dependencies import get_uow
from ...responses import ApiEnvelope, PageData, envelope, page_payload
from ...security import CurrentUser, get_current_user, require_admin
from .schemas import JobResponse, JobRunResponse, JobTriggerRequest
from .service import enqueue_manual_runs

router = APIRouter(
    prefix="/api/jobs",
    tags=["jobs"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=ApiEnvelope[PageData[JobResponse]])
def list_jobs(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    page = uow.jobs.list_page(PageRequest(limit=limit, offset=offset))
    return envelope(page_payload(page.records, page.total))


@router.get("/{job_id}/runs", response_model=ApiEnvelope[PageData[JobRunResponse]])
def list_runs(
    job_id: UUID,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    job = uow.jobs.get(job_id)
    if job is None:
        raise NotFoundError("任务不存在")
    page = uow.job_runs.list_by_job(job.id, PageRequest(limit=limit, offset=offset))
    return envelope(page_payload(page.records, page.total))


@router.post("/{job_id}/run", response_model=ApiEnvelope[list[JobRunResponse]])
def trigger_job(
    job_id: UUID,
    body: JobTriggerRequest,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict[str, object]:
    job = uow.jobs.get(job_id)
    if job is None:
        raise NotFoundError("任务不存在")
    runs = enqueue_manual_runs(
        uow,
        job=job,
        project_id=body.project_id,
        actor=user.username,
        at=utc_now(),
    )
    return envelope(list(runs), message="queued")
