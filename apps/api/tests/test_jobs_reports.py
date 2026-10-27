from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from agent_api.config import Settings
from agent_api.security import create_access_token
from agent_core import (
    CommitRange,
    Job,
    JobKind,
    PageRequest,
    Report,
    ReportItem,
    ReportKind,
    ReportStatus,
    TimeRange,
    utc_now,
)
from agent_data import UnitOfWork


def _create_project(client: TestClient, headers: dict[str, str], path: Path) -> dict[str, object]:
    response = client.post(
        "/api/projects",
        headers=headers,
        json={"name": "项目 A", "path": str(path), "vcs_type": "git", "enabled": True},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _seed_job(session_factory: sessionmaker[Session], *, enabled: bool = True) -> Job:
    now = utc_now()
    job = Job(
        id=uuid4(),
        name="每日 Git 日报",
        kind=JobKind.DAILY_GIT,
        cron="0 2 * * *",
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )
    with UnitOfWork(session_factory) as uow:
        return uow.jobs.add(job)


def _seed_report(
    session_factory: sessionmaker[Session],
    *,
    project_id: UUID,
    start: datetime,
    title: str = "项目 A 日报",
) -> Report:
    now = utc_now()
    report = Report(
        id=uuid4(),
        project_id=project_id,
        job_run_id=None,
        kind=ReportKind.DAILY,
        period=TimeRange(start=start, end=start + timedelta(days=1)),
        title=title,
        body=f"# {title}\n\n正文来自数据库\n",
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
                    title="feat: 增加登录",
                    summary="新增登录接口",
                    category="feature",
                    commit_range=CommitRange(start_commit="abc123", end_commit="abc123"),
                    created_at=now,
                    updated_at=now,
                ),
            )
        )
        return created


def test_admin_trigger_queues_manual_run(
    client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    project = _create_project(client, auth_headers, tmp_path)
    job = _seed_job(session_factory)

    response = client.post(
        f"/api/jobs/{job.id}/run",
        headers=auth_headers,
        json={"project_id": project["id"]},
    )

    assert response.status_code == 200, response.text
    runs = response.json()["data"]
    assert len(runs) == 1
    assert runs[0]["status"] == "pending"
    assert runs[0]["trigger"] == "manual"
    assert runs[0]["project_id"] == project["id"]

    history = client.get(f"/api/jobs/{job.id}/runs", headers=auth_headers)
    assert history.status_code == 200
    assert history.json()["data"]["total"] == 1

    audits = client.get("/admin/audit-logs", headers=auth_headers).json()["data"]["records"]
    assert any(item["action"] == "job.trigger" for item in audits)


def test_readonly_user_cannot_trigger_job(
    client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    project = _create_project(client, auth_headers, tmp_path)
    job = _seed_job(session_factory)
    token = create_access_token("viewer", "viewer", test_settings)

    response = client.post(
        f"/api/jobs/{job.id}/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"project_id": project["id"]},
    )

    assert response.status_code == 403
    with UnitOfWork(session_factory) as uow:
        assert uow.job_runs.list_by_job(job.id, PageRequest()).total == 0


def test_report_detail_returns_items_and_period_filter(
    client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    project = _create_project(client, auth_headers, tmp_path)
    project_id = UUID(str(project["id"]))
    old_start = datetime(2026, 10, 1, tzinfo=UTC)
    new_start = datetime(2026, 10, 20, tzinfo=UTC)
    old_report = _seed_report(
        session_factory, project_id=project_id, start=old_start, title="旧日报"
    )
    new_report = _seed_report(
        session_factory, project_id=project_id, start=new_start, title="新日报"
    )

    detail = client.get(
        f"/api/reports/{new_report.id}?project_id={project_id}", headers=auth_headers
    )
    assert detail.status_code == 200
    body = detail.json()["data"]
    assert body["body"] == new_report.body
    assert body["items"][0]["commit_range"]["start_commit"] == "abc123"

    filtered = client.get(
        "/api/reports",
        headers=auth_headers,
        params={
            "project_id": str(project_id),
            "kind": "daily",
            "period_start": old_start.isoformat(),
            "period_end": (old_start + timedelta(hours=1)).isoformat(),
        },
    )
    assert filtered.status_code == 200, filtered.text
    records = filtered.json()["data"]["records"]
    assert [item["id"] for item in records] == [str(old_report.id)]

    other = client.get(f"/api/reports/{new_report.id}?project_id={uuid4()}", headers=auth_headers)
    assert other.status_code == 404


def test_report_export_does_not_mutate_database(
    client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    project = _create_project(client, auth_headers, tmp_path)
    project_id = UUID(str(project["id"]))
    report = _seed_report(
        session_factory,
        project_id=project_id,
        start=datetime(2026, 10, 26, tzinfo=UTC),
    )

    response = client.get(
        f"/api/reports/{report.id}/export?project_id={project_id}", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.text == report.body
    assert "attachment" in response.headers["content-disposition"]
    with UnitOfWork(session_factory) as uow:
        stored = uow.reports.get(report.id)
        assert stored is not None
        assert stored.body == report.body
        assert stored.updated_at == report.updated_at
