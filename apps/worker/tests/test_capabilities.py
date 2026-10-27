from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from agent_core import (
    CapabilityStatus,
    CommitRange,
    Job,
    JobKind,
    JobRunStatus,
    PageRequest,
    Project,
    Report,
    ReportItem,
    ReportKind,
    ReportStatus,
    TimeRange,
    TriggerType,
    VcsType,
    utc_now,
)
from agent_data import UnitOfWork
from agent_worker.capabilities import sediment_capabilities
from agent_worker.jobs import process_job


def _seed_project(session_factory: sessionmaker[Session], path: Path) -> Project:
    now = utc_now()
    project = Project(
        id=uuid4(),
        name="能力项目",
        path=str(path),
        vcs_type=VcsType.GIT,
        created_at=now,
        updated_at=now,
    )
    with UnitOfWork(session_factory) as uow:
        return uow.projects.add(project)


def _seed_job(session_factory: sessionmaker[Session]) -> Job:
    now = utc_now()
    job = Job(
        id=uuid4(),
        name="能力沉淀",
        kind=JobKind.CAPABILITY_SEDIMENT,
        cron="0 3 * * *",
        config=(("lookback_days", 8),),
        created_at=now,
        updated_at=now,
    )
    with UnitOfWork(session_factory) as uow:
        return uow.jobs.add(job)


def _seed_report(
    session_factory: sessionmaker[Session],
    *,
    project_id: UUID,
    title: str,
    summary: str,
    category: str = "feature",
    period_start: datetime | None = None,
) -> Report:
    now = utc_now()
    start = period_start or datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    report = Report(
        id=uuid4(),
        project_id=project_id,
        job_run_id=None,
        kind=ReportKind.DAILY,
        period=TimeRange(start=start, end=start + timedelta(days=1)),
        title="日报",
        body="日报正文",
        status=ReportStatus.READY,
        created_at=now,
        updated_at=now,
    )
    with UnitOfWork(session_factory) as uow:
        created = uow.reports.add(report)
        uow.report_items.add_many(
            (
                ReportItem(
                    id=uuid4(),
                    report_id=created.id,
                    project_id=project_id,
                    title=title,
                    summary=summary,
                    category=category,
                    commit_range=CommitRange(start_commit="abc123", end_commit="def456"),
                    created_at=now,
                    updated_at=now,
                ),
            )
        )
        return created


def test_capability_sediment_job_persists_sources_and_project(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    project = _seed_project(session_factory, tmp_path)
    report = _seed_report(
        session_factory,
        project_id=project.id,
        title="feat: 增加登录重试",
        summary="登录失败时最多重试三次。",
    )
    job = _seed_job(session_factory)

    runs = process_job(session_factory, job.id, trigger=TriggerType.SCHEDULE)

    assert len(runs) == 1
    assert runs[0].status is JobRunStatus.SUCCEEDED
    assert runs[0].report_id is None
    with UnitOfWork(session_factory) as uow:
        page = uow.capabilities.list_by_project(project.id, PageRequest())
        assert page.total == 1
        note = page.records[0]
        assert note.topic == "增加登录重试"
        assert note.project_id == project.id
        assert note.source_report_ids == (report.id,)
        assert note.status is CapabilityStatus.DRAFT
        assert note.tags == ("feature",)


def test_same_topic_merges_sources_without_creating_duplicate(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    project = _seed_project(session_factory, tmp_path)
    now = datetime.now(UTC)
    first_report = _seed_report(
        session_factory,
        project_id=project.id,
        title="feat: 登录重试",
        summary="第一次实现。",
        period_start=now - timedelta(days=2),
    )
    second_report = _seed_report(
        session_factory,
        project_id=project.id,
        title="fix: 登录重试",
        summary="修复重试次数边界。",
        category="fix",
        period_start=now - timedelta(days=1),
    )

    first = sediment_capabilities(session_factory, project, at=now)
    second = sediment_capabilities(session_factory, project, at=now)

    assert first.created == 1
    assert second.updated + second.skipped == 2
    with UnitOfWork(session_factory) as uow:
        page = uow.capabilities.list_by_project(project.id, PageRequest())
        assert page.total == 1
        note = page.records[0]
        assert set(note.source_report_ids) == {first_report.id, second_report.id}
        assert len(note.source_report_ids) == 2
        assert "第一次实现" in note.content
        assert "修复重试次数边界" in note.content
        assert set(note.tags) == {"feature", "fix"}


def test_merge_keeps_confirmed_status(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    project = _seed_project(session_factory, tmp_path)
    now = datetime.now(UTC)
    _seed_report(
        session_factory,
        project_id=project.id,
        title="docs: 部署说明",
        summary="补充部署文档。",
        category="docs",
        period_start=now - timedelta(days=1),
    )
    sediment_capabilities(session_factory, project, at=now)
    with UnitOfWork(session_factory) as uow:
        note = uow.capabilities.list_by_project(project.id, PageRequest()).records[0]
        uow.capabilities.update(replace(note, status=CapabilityStatus.CONFIRMED))

    _seed_report(
        session_factory,
        project_id=project.id,
        title="docs: 部署说明",
        summary="再次确认部署步骤。",
        category="docs",
    )
    sediment_capabilities(session_factory, project, at=now)

    with UnitOfWork(session_factory) as uow:
        note = uow.capabilities.list_by_project(project.id, PageRequest()).records[0]
        assert note.status is CapabilityStatus.CONFIRMED
