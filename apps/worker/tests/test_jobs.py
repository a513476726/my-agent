from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from agent_core import (
    Job,
    JobKind,
    JobRun,
    JobRunStatus,
    PageRequest,
    Project,
    ReportKind,
    TriggerType,
    VcsType,
    period_for,
    utc_now,
)
from agent_data import UnitOfWork
from agent_worker.jobs import process_job, process_pending_runs
from agent_worker.scheduler import build_scheduler, sync_schedules


def _seed_project(
    session_factory: sessionmaker[Session],
    path: Path,
    *,
    name: str,
    enabled: bool = True,
) -> Project:
    now = utc_now()
    project = Project(
        id=uuid4(),
        name=name,
        path=str(path),
        vcs_type=VcsType.GIT,
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )
    with UnitOfWork(session_factory) as uow:
        return uow.projects.add(project)


def _seed_job(
    session_factory: sessionmaker[Session],
    *,
    name: str = "每日 Git 日报",
    enabled: bool = True,
) -> Job:
    now = utc_now()
    job = Job(
        id=uuid4(),
        name=name,
        kind=JobKind.DAILY_GIT,
        cron="0 2 * * *",
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )
    with UnitOfWork(session_factory) as uow:
        return uow.jobs.add(job)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "测试用户"], cwd=path, check=True)


def _commit(path: Path, message: str, content: str) -> None:
    (path / "app.py").write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path,
        check=True,
        capture_output=True,
    )


def test_daily_job_persists_report_and_is_idempotent(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    _init_repo(tmp_path)
    _commit(tmp_path, "feat: 增加登录", "def login():\n    return True\n")
    _commit(tmp_path, "fix: 修复退出", "def logout():\n    return True\n")
    project = _seed_project(session_factory, tmp_path, name="项目 A")
    job = _seed_job(session_factory)
    now = datetime.now(UTC)

    first = process_job(
        session_factory,
        job.id,
        trigger=TriggerType.SCHEDULE,
        at=now,
    )

    assert len(first) == 1
    assert first[0].status is JobRunStatus.SUCCEEDED
    assert first[0].report_id is not None
    with UnitOfWork(session_factory) as uow:
        report = uow.reports.get(first[0].report_id)
        assert report is not None
        assert "增加登录" in report.body
        items = uow.report_items.list_by_report(report.id)
        assert len(items) == 2
        assert items[0].commit_range.start_commit
        assert items[0].project_id == project.id

    second = process_job(
        session_factory,
        job.id,
        trigger=TriggerType.MANUAL,
        at=now,
    )
    assert second[0].id == first[0].id
    with UnitOfWork(session_factory) as uow:
        page = uow.reports.list_by_project(project.id, PageRequest())
        assert page.total == 1


def test_failure_in_one_project_does_not_block_other_projects(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    valid = tmp_path / "valid"
    invalid = tmp_path / "missing"
    _init_repo(valid)
    _commit(valid, "docs: 更新说明", "hello\n")
    valid_project = _seed_project(session_factory, valid, name="正常项目")
    _seed_project(session_factory, invalid, name="损坏项目")
    job = _seed_job(session_factory)

    runs = process_job(
        session_factory,
        job.id,
        trigger=TriggerType.SCHEDULE,
    )

    statuses = {str(run.project_id): run.status for run in runs}
    assert set(statuses.values()) == {JobRunStatus.SUCCEEDED, JobRunStatus.FAILED}
    failed = [run for run in runs if run.status is JobRunStatus.FAILED]
    assert "项目目录不存在" in (failed[0].error_message or "")
    with UnitOfWork(session_factory) as uow:
        page = uow.reports.list_by_project(valid_project.id, PageRequest())
        assert page.total == 1
        assert page.records[0].period.start.tzinfo is not None


def test_failed_run_can_be_retried_with_same_run_key(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    _seed_project(session_factory, tmp_path, name="稍后创建")
    job = _seed_job(session_factory)
    now = datetime.now(UTC)

    first = process_job(
        session_factory,
        job.id,
        trigger=TriggerType.SCHEDULE,
        at=now,
    )
    assert first[0].status is JobRunStatus.FAILED

    _init_repo(tmp_path)
    _commit(tmp_path, "feat: 恢复", "restored\n")
    second = process_job(
        session_factory,
        job.id,
        trigger=TriggerType.MANUAL,
        at=now,
    )

    assert second[0].id == first[0].id
    assert second[0].status is JobRunStatus.SUCCEEDED
    assert second[0].report_id is not None


def test_scheduler_loads_only_enabled_jobs(
    session_factory: sessionmaker[Session],
) -> None:
    enabled = _seed_job(session_factory, name="启用任务", enabled=True)
    disabled = _seed_job(session_factory, name="停用任务", enabled=False)
    scheduler = build_scheduler(session_factory)
    try:
        cron_ids = {job.id for job in scheduler.get_jobs() if job.id.startswith("cron:")}
        assert f"cron:{enabled.id}" in cron_ids
        assert f"cron:{disabled.id}" not in cron_ids

        with UnitOfWork(session_factory) as uow:
            job = uow.jobs.get(enabled.id)
            assert job is not None
            uow.jobs.update(
                Job(
                    id=job.id,
                    name=job.name,
                    kind=job.kind,
                    cron=job.cron,
                    enabled=False,
                    config=job.config,
                    created_at=job.created_at,
                    updated_at=utc_now(),
                )
            )
        sync_schedules(scheduler, session_factory)
        cron_ids = {job.id for job in scheduler.get_jobs() if job.id.startswith("cron:")}
        assert f"cron:{enabled.id}" not in cron_ids
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_pending_manual_run_is_processed_by_worker(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    _init_repo(tmp_path)
    _commit(tmp_path, "feat: 手动任务", "manual\n")
    _seed_project(session_factory, tmp_path, name="项目 A")
    job = _seed_job(session_factory)
    now = datetime.now(UTC)
    with UnitOfWork(session_factory) as uow:
        uow.job_runs.add(
            JobRun(
                id=uuid4(),
                job_id=job.id,
                project_id=uow.projects.list(PageRequest()).records[0].id,
                run_key=f"{job.id}:{uuid4()}:{period_for(ReportKind.DAILY, now).key}",
                status=JobRunStatus.PENDING,
                trigger=TriggerType.MANUAL,
                created_at=now,
                updated_at=now,
            )
        )

    processed = process_pending_runs(session_factory)

    assert len(processed) == 1
    assert processed[0].status is JobRunStatus.SUCCEEDED
