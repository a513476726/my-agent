from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from agent_core import Document, DocumentStatus, Job, JobKind, JobRun, PageRequest, Project, VcsType
from agent_data import UnitOfWork

NOW = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


def make_project(name: str, *, offset_seconds: int = 0) -> Project:
    created_at = NOW + timedelta(seconds=offset_seconds)
    return Project(
        id=uuid4(),
        name=name,
        path=f"/workspace/{name}",
        vcs_type=VcsType.GIT,
        created_at=created_at,
        updated_at=created_at,
    )


def make_job(name: str) -> Job:
    return Job(
        id=uuid4(),
        name=name,
        kind=JobKind.DAILY_GIT,
        cron="0 1 * * *",
        created_at=NOW,
        updated_at=NOW,
    )


def make_document(project: Project, suffix: str = "a") -> Document:
    return Document(
        id=uuid4(),
        project_id=project.id,
        knowledge_base_id=None,
        title=f"需求-{suffix}.md",
        source_path=f"docs/需求-{suffix}.md",
        content_hash=f"hash-{suffix}",
        version="v1",
        external_document_id=f"ragflow-doc-{suffix}",
        status=DocumentStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )


def test_project_pagination(session_factory: sessionmaker[Session]) -> None:
    with UnitOfWork(session_factory) as uow:
        for index in range(5):
            uow.projects.add(make_project(f"p{index}", offset_seconds=index))

    with UnitOfWork(session_factory) as uow:
        page = uow.projects.list(PageRequest(limit=2, offset=2))

    assert page.total == 5
    assert [project.name for project in page.records] == ["p2", "p3"]


def test_transaction_rollback(session_factory: sessionmaker[Session]) -> None:
    with pytest.raises(RuntimeError), UnitOfWork(session_factory) as uow:
        uow.projects.add(make_project("rolled-back"))
        raise RuntimeError("boom")

    with UnitOfWork(session_factory) as uow:
        page = uow.projects.list(PageRequest())

    assert page.total == 0


def test_job_run_key_is_unique(session_factory: sessionmaker[Session]) -> None:
    project = make_project("project")
    job = make_job("daily")
    run = JobRun(
        id=uuid4(),
        job_id=job.id,
        project_id=project.id,
        run_key="daily:project:2026-01-01",
        created_at=NOW,
        updated_at=NOW,
    )

    with UnitOfWork(session_factory) as uow:
        uow.projects.add(project)
        uow.jobs.add(job)
        uow.job_runs.add(run)

    with UnitOfWork(session_factory) as uow:
        assert uow.job_runs.find_by_run_key(run.run_key) is not None

    with pytest.raises(IntegrityError), UnitOfWork(session_factory) as uow:
        uow.job_runs.add(
            JobRun(
                id=uuid4(),
                job_id=job.id,
                project_id=project.id,
                run_key=run.run_key,
                created_at=NOW,
                updated_at=NOW,
            )
        )


def test_document_external_id_round_trip(session_factory: sessionmaker[Session]) -> None:
    project = make_project("document-project")
    document = make_document(project)

    with UnitOfWork(session_factory) as uow:
        uow.projects.add(project)
        uow.documents.add(document)

    with UnitOfWork(session_factory) as uow:
        loaded = uow.documents.get(document.id)

    assert loaded is not None
    assert loaded.external_document_id == "ragflow-doc-a"
