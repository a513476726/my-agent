from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from agent_core import (
    AuditLog,
    ConflictError,
    Job,
    JobRun,
    JobRunStatus,
    NotFoundError,
    PageRequest,
    Project,
    ReportKind,
    TriggerType,
    period_for,
    report_kind_for_job,
)
from agent_data import UnitOfWork


def enqueue_manual_runs(
    uow: UnitOfWork,
    *,
    job: Job,
    project_id: UUID | None,
    actor: str,
    at: datetime,
) -> tuple[JobRun, ...]:
    if not job.enabled:
        raise ConflictError("任务已停用")
    projects = _target_projects(uow, project_id)
    try:
        report_kind = report_kind_for_job(job.kind)
    except Exception:
        report_kind = ReportKind.DAILY
    period = period_for(report_kind, at)
    runs: list[JobRun] = []
    for project in projects:
        run_key = f"{job.id}:{project.id}:{period.key}"
        existing = uow.job_runs.find_by_run_key(run_key)
        if existing is not None:
            if existing.status in (
                JobRunStatus.SUCCEEDED,
                JobRunStatus.RUNNING,
                JobRunStatus.SKIPPED,
            ):
                runs.append(existing)
                continue
            runs.append(
                uow.job_runs.update(
                    replace(
                        existing,
                        status=JobRunStatus.PENDING,
                        trigger=TriggerType.MANUAL,
                        started_at=None,
                        finished_at=None,
                        error_message=None,
                        updated_at=at,
                    )
                )
            )
            continue
        runs.append(
            uow.job_runs.add(
                JobRun(
                    id=uuid4(),
                    job_id=job.id,
                    project_id=project.id,
                    run_key=run_key,
                    status=JobRunStatus.PENDING,
                    trigger=TriggerType.MANUAL,
                    created_at=at,
                    updated_at=at,
                )
            )
        )

    uow.audit_logs.add(
        AuditLog(
            id=uuid4(),
            actor=actor,
            action="job.trigger",
            resource_type="job",
            resource_id=str(job.id),
            detail={"run_ids": [str(run.id) for run in runs]},
            created_at=at,
            updated_at=at,
        )
    )
    return tuple(runs)


def _target_projects(uow: UnitOfWork, project_id: UUID | None) -> tuple[Project, ...]:
    if project_id is not None:
        project = uow.projects.get(project_id)
        if project is None:
            raise NotFoundError("项目不存在")
        if not project.enabled:
            raise ConflictError("项目已停用")
        return (project,)

    records: list[Project] = []
    offset = 0
    while True:
        page = uow.projects.list(PageRequest(limit=200, offset=offset), enabled=True)
        records.extend(page.records)
        offset += len(page.records)
        if offset >= page.total or not page.records:
            break
    return tuple(records)
