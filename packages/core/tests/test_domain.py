from datetime import UTC, datetime
from uuid import uuid4

import pytest

from agent_core import (
    CapabilityNote,
    CapabilityStatus,
    Citation,
    CommitRange,
    DomainValidationError,
    JobRun,
    JobRunStatus,
    Page,
    PageRequest,
    Project,
    Report,
    ReportKind,
    RetrievalQuery,
    TimeRange,
    TriggerType,
    VcsType,
)

NOW = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
PROJECT_ID = uuid4()


def make_project(**overrides: object) -> Project:
    values: dict[str, object] = {
        "id": uuid4(),
        "name": "项目 A",
        "path": "/workspace/a",
        "vcs_type": VcsType.GIT,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return Project(**values)  # type: ignore[arg-type]


def test_entity_is_immutable() -> None:
    project = make_project()

    with pytest.raises(AttributeError):
        project.name = "项目 B"  # type: ignore[misc]


@pytest.mark.parametrize(("field", "value"), [("name", " "), ("path", "relative/path")])
def test_project_rejects_invalid_fields(field: str, value: str) -> None:
    with pytest.raises(DomainValidationError):
        make_project(**{field: value})


def test_page_rejects_negative_total() -> None:
    with pytest.raises(DomainValidationError):
        Page(records=(), total=-1)


def test_page_rejects_records_exceeding_total() -> None:
    with pytest.raises(DomainValidationError):
        Page(records=(1,), total=0)


def test_page_keeps_records_and_total() -> None:
    page = Page(records=(1, 2), total=5)

    assert page.records == (1, 2)
    assert page.total == 5


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": 201}, {"offset": -1}])
def test_page_request_rejects_invalid_bounds(kwargs: dict[str, int]) -> None:
    with pytest.raises(DomainValidationError):
        PageRequest(**kwargs)


def test_time_range_rejects_empty_range() -> None:
    with pytest.raises(DomainValidationError):
        TimeRange(start=NOW, end=NOW)


def test_report_requires_title() -> None:
    with pytest.raises(DomainValidationError):
        Report(
            id=uuid4(),
            project_id=PROJECT_ID,
            job_run_id=None,
            kind=ReportKind.DAILY,
            period=TimeRange(start=NOW, end=NOW.replace(hour=9)),
            title=" ",
            body="正文",
            created_at=NOW,
            updated_at=NOW,
        )


def test_capability_note_requires_source_report() -> None:
    with pytest.raises(DomainValidationError):
        CapabilityNote(
            id=uuid4(),
            project_id=PROJECT_ID,
            source_report_ids=(),
            topic="事务边界",
            content="内容",
            tags=("backend",),
            status=CapabilityStatus.DRAFT,
            created_at=NOW,
            updated_at=NOW,
        )


def test_job_run_requires_run_key() -> None:
    with pytest.raises(DomainValidationError):
        JobRun(
            id=uuid4(),
            job_id=uuid4(),
            project_id=PROJECT_ID,
            run_key=" ",
            status=JobRunStatus.PENDING,
            trigger=TriggerType.MANUAL,
            started_at=None,
            finished_at=None,
            error_message=None,
            report_id=None,
            created_at=NOW,
            updated_at=NOW,
        )


def test_retrieval_query_rejects_blank_text() -> None:
    with pytest.raises(DomainValidationError):
        RetrievalQuery(project_id=PROJECT_ID, text=" ", top_k=5)


@pytest.mark.parametrize("top_k", [0, 51])
def test_retrieval_query_rejects_invalid_top_k(top_k: int) -> None:
    with pytest.raises(DomainValidationError):
        RetrievalQuery(project_id=PROJECT_ID, text="需求", top_k=top_k)


def test_citation_rejects_negative_score() -> None:
    with pytest.raises(DomainValidationError):
        Citation(
            document_id=uuid4(),
            document_title="产品需求",
            heading_path=("第二章",),
            snippet="内容",
            score=-0.1,
        )


def test_commit_range_requires_both_ends() -> None:
    with pytest.raises(DomainValidationError):
        CommitRange(start_commit="", end_commit="abc123")
