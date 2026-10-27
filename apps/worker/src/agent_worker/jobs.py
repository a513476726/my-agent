from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from agent_core import (
    AuditLog,
    CommitRange,
    ConflictError,
    DomainError,
    Job,
    JobKind,
    JobRun,
    JobRunStatus,
    NotFoundError,
    PageRequest,
    Project,
    Report,
    ReportItem,
    ReportKind,
    ReportStatus,
    TimeRange,
    TriggerType,
    period_for,
    report_kind_for_job,
    utc_now,
)
from agent_data import UnitOfWork

from .capabilities import sediment_capabilities
from .reports import ReportItemDraft, build_report_draft, collect_git_changes

logger = logging.getLogger(__name__)


def enqueue_job(
    session_factory: sessionmaker[Session],
    job_id: UUID,
    *,
    trigger: TriggerType,
    actor: str,
    project_id: UUID | None = None,
    at: datetime | None = None,
) -> tuple[JobRun, ...]:
    now = at or utc_now()
    with UnitOfWork(session_factory) as uow:
        job = uow.jobs.get(job_id)
        if job is None:
            raise NotFoundError("任务不存在")
        if not job.enabled:
            raise ConflictError("任务已停用")
        projects = _target_projects(uow, project_id)
        if not projects:
            return ()
        period = period_for(_period_kind_for_job(job.kind), now)
        runs: list[JobRun] = []
        for project in projects:
            run_key = f"{job.id}:{project.id}:{period.key}"
            existing = uow.job_runs.find_by_run_key(run_key)
            if existing is not None:
                if existing.status in (JobRunStatus.SUCCEEDED, JobRunStatus.RUNNING):
                    runs.append(existing)
                    continue
                if existing.status is JobRunStatus.SKIPPED:
                    continue
                updated = replace(
                    existing,
                    status=JobRunStatus.PENDING,
                    trigger=trigger,
                    started_at=None,
                    finished_at=None,
                    error_message=None,
                    updated_at=now,
                )
                runs.append(uow.job_runs.update(updated))
                continue
            runs.append(
                uow.job_runs.add(
                    JobRun(
                        id=uuid4(),
                        job_id=job.id,
                        project_id=project.id,
                        run_key=run_key,
                        status=JobRunStatus.PENDING,
                        trigger=trigger,
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
        if runs:
            uow.audit_logs.add(
                AuditLog(
                    id=uuid4(),
                    actor=actor,
                    action="job.enqueue",
                    resource_type="job",
                    resource_id=str(job.id),
                    detail={
                        "trigger": trigger.value,
                        "run_ids": [str(run.id) for run in runs],
                    },
                    created_at=now,
                    updated_at=now,
                )
            )
        return tuple(runs)


def process_job(
    session_factory: sessionmaker[Session],
    job_id: UUID,
    *,
    trigger: TriggerType,
    actor: str = "scheduler",
    project_id: UUID | None = None,
    at: datetime | None = None,
) -> tuple[JobRun, ...]:
    runs = enqueue_job(
        session_factory,
        job_id,
        trigger=trigger,
        actor=actor,
        project_id=project_id,
        at=at,
    )
    return tuple(_process_run(session_factory, run.id) for run in runs)


def process_pending_runs(
    session_factory: sessionmaker[Session],
    *,
    limit: int = 100,
) -> tuple[JobRun, ...]:
    with UnitOfWork(session_factory) as uow:
        pending = uow.job_runs.list_pending(limit)
    return tuple(_process_run(session_factory, run.id) for run in pending)


def _process_run(session_factory: sessionmaker[Session], run_id: UUID) -> JobRun:
    now = utc_now()
    with UnitOfWork(session_factory) as uow:
        run = uow.job_runs.get(run_id)
        if run is None:
            raise NotFoundError("运行记录不存在")
        if run.status is not JobRunStatus.PENDING:
            return run
        job = uow.jobs.get(run.job_id)
        project = uow.projects.get(run.project_id)
        if job is None or project is None:
            failed = _mark_failed(
                uow,
                run,
                "任务或项目已不存在",
                now,
            )
            return failed
        running = uow.job_runs.update(
            replace(
                run,
                status=JobRunStatus.RUNNING,
                started_at=now,
                updated_at=now,
            )
        )
        uow.commit()

    try:
        if not job.enabled or not project.enabled:
            raise ConflictError("任务或项目已停用")
        if job.kind is JobKind.CAPABILITY_SEDIMENT:
            return _process_capability_sediment(
                session_factory,
                running=running,
                project=project,
                job=job,
            )

        report_kind = report_kind_for_job(job.kind)
        period = period_for(report_kind, running.created_at)
        changes = collect_git_changes(project, period)
        draft = build_report_draft(project, period, changes)
        return _persist_report(
            session_factory,
            running=running,
            project=project,
            report_kind=report_kind,
            period_start=period.start,
            period_end=period.end,
            title=draft.title,
            body=draft.body,
            item_drafts=draft.items,
        )
    except Exception as exc:
        logger.exception("任务运行失败: run_id=%s", run_id)
        with UnitOfWork(session_factory) as uow:
            current = uow.job_runs.get(run_id)
            if current is None:
                raise
            return _mark_failed(uow, current, _error_message(exc), utc_now())


def _period_kind_for_job(kind: JobKind) -> ReportKind:
    try:
        return report_kind_for_job(kind)
    except DomainError:
        return ReportKind.DAILY


def _process_capability_sediment(
    session_factory: sessionmaker[Session],
    *,
    running: JobRun,
    project: Project,
    job: Job,
) -> JobRun:
    config = dict(job.config)
    lookback_days = _positive_int(config.get("lookback_days"), default=8)
    result = sediment_capabilities(
        session_factory,
        project,
        at=running.created_at,
        lookback_days=lookback_days,
    )
    now = utc_now()
    with UnitOfWork(session_factory) as uow:
        current = uow.job_runs.get(running.id)
        if current is None:
            raise NotFoundError("运行记录不存在")
        completed = uow.job_runs.update(
            replace(
                current,
                status=JobRunStatus.SUCCEEDED,
                finished_at=now,
                error_message=None,
                updated_at=now,
            )
        )
        uow.audit_logs.add(
            AuditLog(
                id=uuid4(),
                actor="scheduler",
                action="job.run.capability_sediment",
                resource_type="job_run",
                resource_id=str(completed.id),
                project_id=project.id,
                detail=result.to_dict(),
                created_at=now,
                updated_at=now,
            )
        )
        return completed


def _positive_int(value: object, *, default: int) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _persist_report(
    session_factory: sessionmaker[Session],
    *,
    running: JobRun,
    project: Project,
    report_kind: ReportKind,
    period_start: datetime,
    period_end: datetime,
    title: str,
    body: str,
    item_drafts: tuple[ReportItemDraft, ...],
) -> JobRun:
    now = utc_now()
    with UnitOfWork(session_factory) as uow:
        existing = uow.reports.find_by_period(project.id, report_kind, period_start, period_end)
        if existing is None:
            report = uow.reports.add(
                Report(
                    id=uuid4(),
                    project_id=project.id,
                    job_run_id=running.id,
                    kind=report_kind,
                    period=TimeRange(start=period_start, end=period_end),
                    title=title,
                    body=body,
                    status=ReportStatus.READY,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            uow.report_items.delete_by_report(existing.id)
            report = uow.reports.update(
                replace(
                    existing,
                    job_run_id=running.id,
                    title=title,
                    body=body,
                    status=ReportStatus.READY,
                    updated_at=now,
                )
            )

        items: list[ReportItem] = []
        for draft in item_drafts:
            items.append(
                ReportItem(
                    id=uuid4(),
                    report_id=report.id,
                    project_id=project.id,
                    title=draft.title,
                    summary=draft.summary,
                    category=draft.category,
                    commit_range=CommitRange(
                        start_commit=draft.start_commit,
                        end_commit=draft.end_commit,
                    ),
                    created_at=now,
                    updated_at=now,
                )
            )
        if items:
            uow.report_items.add_many(tuple(items))

        current = uow.job_runs.get(running.id)
        if current is None:
            raise NotFoundError("运行记录不存在")
        completed = uow.job_runs.update(
            replace(
                current,
                status=JobRunStatus.SUCCEEDED,
                finished_at=now,
                error_message=None,
                report_id=report.id,
                updated_at=now,
            )
        )
        uow.audit_logs.add(
            AuditLog(
                id=uuid4(),
                actor="scheduler",
                action="job.run.succeeded",
                resource_type="job_run",
                resource_id=str(completed.id),
                project_id=project.id,
                detail={"report_id": str(report.id), "items": len(items)},
                created_at=now,
                updated_at=now,
            )
        )
        return completed


def _mark_failed(
    uow: UnitOfWork,
    run: JobRun,
    message: str,
    now: datetime,
) -> JobRun:
    failed = uow.job_runs.update(
        replace(
            run,
            status=JobRunStatus.FAILED,
            finished_at=now,
            error_message=message[:4000],
            updated_at=now,
        )
    )
    uow.audit_logs.add(
        AuditLog(
            id=uuid4(),
            actor="scheduler",
            action="job.run.failed",
            resource_type="job_run",
            resource_id=str(failed.id),
            project_id=failed.project_id,
            detail={"error": failed.error_message},
            created_at=now,
            updated_at=now,
        )
    )
    return failed


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


def _error_message(exc: Exception) -> str:
    if isinstance(exc, DomainError):
        return exc.message
    return f"{type(exc).__name__}: {exc}"
