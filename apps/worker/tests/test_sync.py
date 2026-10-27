from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

import agent_worker.sync as sync_module
from agent_core import DomainValidationError, PageRequest, Project, VcsType, utc_now
from agent_data import UnitOfWork
from agent_worker.knowledge import KnowledgeDataset, KnowledgeDocument
from agent_worker.sync import main, sync_project


class FakeKnowledge:
    def __init__(self, *, fail_on_filename: str | None = None) -> None:
        self.fail_on_filename = fail_on_filename
        self.ensures: list[tuple[UUID, str]] = []
        self.uploads: list[tuple[UUID, str, str, bytes]] = []
        self.deletes: list[tuple[str, str]] = []

    def ensure_dataset(self, project_id: UUID, name: str) -> KnowledgeDataset:
        self.ensures.append((project_id, name))
        return KnowledgeDataset(project_id=project_id, dataset_id="dataset-1", name=name)

    def upload_document(
        self,
        project_id: UUID,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> KnowledgeDocument:
        if filename == self.fail_on_filename:
            raise RuntimeError("上传失败")
        self.uploads.append((project_id, dataset_id, filename, content))
        return KnowledgeDocument(
            dataset_id=dataset_id,
            document_id=f"document-{len(self.uploads)}",
            filename=filename,
            parse_started=True,
        )

    def delete_document(self, project_id: UUID, dataset_id: str, document_id: str) -> None:
        self.deletes.append((dataset_id, document_id))

    def __enter__(self) -> FakeKnowledge:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        pass


def _make_project(path: Path) -> Project:
    now = utc_now()
    return Project(
        id=uuid4(),
        name="项目 A",
        path=str(path),
        vcs_type=VcsType.GIT,
        created_at=now,
        updated_at=now,
    )


def _store_project(session_factory: sessionmaker[Session], project: Project) -> None:
    with UnitOfWork(session_factory) as uow:
        uow.projects.add(project)


def test_sync_counts_added_skipped_and_updated(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    project_root = tmp_path / "repo"
    documents_dir = project_root / "docs"
    documents_dir.mkdir(parents=True)
    (documents_dir / "a.md").write_text("旧内容", encoding="utf-8")
    (documents_dir / "b.pdf").write_bytes(b"pdf-content")
    (documents_dir / "ignored.zip").write_bytes(b"zip-content")
    project = _make_project(project_root)
    _store_project(session_factory, project)
    knowledge = FakeKnowledge()

    first = sync_project(
        session_factory,
        knowledge,
        project,
        actor="tester",
        source_dir="docs",
    )
    second = sync_project(
        session_factory,
        knowledge,
        project,
        actor="tester",
        source_dir="docs",
    )

    (documents_dir / "a.md").write_text("新内容", encoding="utf-8")
    third = sync_project(
        session_factory,
        knowledge,
        project,
        actor="tester",
        source_dir="docs",
    )

    assert first.to_dict() == {"added": 2, "updated": 0, "skipped": 0, "failed": []}
    assert second.to_dict() == {"added": 0, "updated": 0, "skipped": 2, "failed": []}
    assert third.to_dict() == {"added": 0, "updated": 1, "skipped": 1, "failed": []}
    assert [upload[2] for upload in knowledge.uploads] == ["a.md", "b.pdf", "a.md"]
    assert knowledge.deletes == [("dataset-1", "document-1")]

    with UnitOfWork(session_factory) as uow:
        updated = uow.documents.find_by_source_path(project.id, "docs/a.md")
        assert updated is not None
        assert updated.external_document_id == "document-3"
        assert updated.version == hashlib.sha256("新内容".encode()).hexdigest()
        audit = uow.audit_logs.list(PageRequest(limit=20), project_id=project.id)

    update_log = next(log for log in audit.records if log.action == "document.sync.update")
    assert update_log.detail is not None
    assert update_log.detail["previous_content_hash"] is not None


def test_sync_skips_same_content_at_different_path(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    project_root = tmp_path / "repo"
    documents_dir = project_root / "docs"
    documents_dir.mkdir(parents=True)
    (documents_dir / "a.md").write_text("同一份内容", encoding="utf-8")
    (documents_dir / "copy.md").write_text("同一份内容", encoding="utf-8")
    project = _make_project(project_root)
    _store_project(session_factory, project)
    knowledge = FakeKnowledge()

    result = sync_project(
        session_factory,
        knowledge,
        project,
        actor="tester",
        source_dir="docs",
    )

    assert result.to_dict() == {"added": 1, "updated": 0, "skipped": 1, "failed": []}
    assert len(knowledge.uploads) == 1


def test_sync_failure_does_not_block_other_documents(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    project_root = tmp_path / "repo"
    documents_dir = project_root / "docs"
    documents_dir.mkdir(parents=True)
    (documents_dir / "bad.md").write_text("失败", encoding="utf-8")
    (documents_dir / "good.md").write_text("成功", encoding="utf-8")
    project = _make_project(project_root)
    _store_project(session_factory, project)
    knowledge = FakeKnowledge(fail_on_filename="bad.md")

    result = sync_project(
        session_factory,
        knowledge,
        project,
        actor="tester",
        source_dir="docs",
    )

    assert result.added == 1
    assert result.updated == 0
    assert result.skipped == 0
    assert len(result.failed) == 1
    assert result.failed[0].source_path == "docs/bad.md"
    with UnitOfWork(session_factory) as uow:
        listing = uow.documents.list_by_project(project.id, PageRequest())
    assert [document.source_path for document in listing.records] == ["docs/good.md"]


def test_sync_rejects_source_dir_outside_project(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    project_root = tmp_path / "repo"
    project_root.mkdir()
    project = _make_project(project_root)
    _store_project(session_factory, project)

    with pytest.raises(DomainValidationError):
        sync_project(
            session_factory,
            FakeKnowledge(),
            project,
            actor="tester",
            source_dir="../outside",
        )


def test_sync_command_prints_counts(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_root = tmp_path / "repo"
    documents_dir = project_root / "docs"
    documents_dir.mkdir(parents=True)
    (documents_dir / "需求.md").write_text("命令测试", encoding="utf-8")
    project = _make_project(project_root)
    _store_project(session_factory, project)
    knowledge = FakeKnowledge()
    monkeypatch.setattr(sync_module, "HttpKnowledgeClient", lambda **kwargs: knowledge)

    exit_code = main(
        [
            "--project-id",
            str(project.id),
            "--source-dir",
            "docs",
            "--actor",
            "tester",
            "--database-url",
            database_url,
        ]
    )

    assert exit_code == 0
    assert knowledge.uploads[0][2] == "需求.md"
    output = capsys.readouterr().out
    assert '"added": 1' in output
