from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from agent_api.dependencies import get_knowledge_client
from agent_api.knowledge import KnowledgeDataset, KnowledgeDocument
from agent_core import CapabilityNote, CapabilityStatus, PageRequest, utc_now
from agent_data import UnitOfWork


class FakeKnowledge:
    def __init__(self) -> None:
        self.uploads: list[tuple[UUID, str, str, bytes]] = []
        self.deleted: list[tuple[UUID, str, str]] = []

    def ensure_dataset(self, project_id: UUID, name: str) -> KnowledgeDataset:
        return KnowledgeDataset(
            project_id=project_id,
            dataset_id=f"dataset-{project_id}",
            name=name,
        )

    def upload_document(
        self,
        project_id: UUID,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> KnowledgeDocument:
        self.uploads.append((project_id, dataset_id, filename, content))
        return KnowledgeDocument(
            dataset_id=dataset_id,
            document_id=f"doc-{len(self.uploads)}",
            filename=filename,
            parse_started=True,
        )

    def delete_document(self, project_id: UUID, dataset_id: str, document_id: str) -> None:
        self.deleted.append((project_id, dataset_id, document_id))


def _create_project(client: TestClient, headers: dict[str, str], path: Path) -> dict[str, object]:
    response = client.post(
        "/api/projects",
        headers=headers,
        json={"name": "项目 A", "path": str(path), "vcs_type": "git", "enabled": True},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _seed_note(
    session_factory: sessionmaker[Session],
    *,
    project_id: UUID,
    topic: str,
    content: str,
    tags: tuple[str, ...],
    status: CapabilityStatus = CapabilityStatus.CONFIRMED,
) -> CapabilityNote:
    now = utc_now()
    note = CapabilityNote(
        id=uuid4(),
        project_id=project_id,
        source_report_ids=(uuid4(),),
        topic=topic,
        content=content,
        tags=tags,
        status=status,
        created_at=now,
        updated_at=now,
    )
    with UnitOfWork(session_factory) as uow:
        return uow.capabilities.add(note)


def test_capability_search_hides_drafts_and_supports_filters(
    client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    project = _create_project(client, auth_headers, tmp_path)
    project_id = UUID(str(project["id"]))
    auth_note = _seed_note(
        session_factory,
        project_id=project_id,
        topic="登录重试",
        content="登录失败重试三次",
        tags=("auth", "feature"),
    )
    _seed_note(
        session_factory,
        project_id=project_id,
        topic="部署说明",
        content="使用只读挂载",
        tags=("ops",),
    )
    draft = _seed_note(
        session_factory,
        project_id=project_id,
        topic="登录审计",
        content="记录登录审计",
        tags=("auth", "feature"),
        status=CapabilityStatus.DRAFT,
    )

    search = client.get(f"/api/capabilities/search?project_id={project_id}", headers=auth_headers)
    assert search.status_code == 200
    assert search.json()["data"]["total"] == 2
    assert str(draft.id) not in {item["id"] for item in search.json()["data"]["records"]}

    filtered = client.get(
        "/api/capabilities/search",
        headers=auth_headers,
        params=[
            ("project_id", str(project_id)),
            ("topic", auth_note.topic),
            ("tags", "auth"),
            ("tags", "feature"),
        ],
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["data"]["records"]] == [str(auth_note.id)]

    listing = client.get(f"/api/capabilities?project_id={project_id}", headers=auth_headers)
    assert listing.json()["data"]["total"] == 3

    confirmed = client.patch(
        f"/api/capabilities/{draft.id}",
        headers=auth_headers,
        json={"project_id": str(project_id), "status": "confirmed"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["status"] == "confirmed"

    search = client.get(f"/api/capabilities/search?project_id={project_id}", headers=auth_headers)
    assert search.json()["data"]["total"] == 3
    audits = client.get("/admin/audit-logs", headers=auth_headers).json()["data"]["records"]
    assert any(item["action"] == "capability.status.update" for item in audits)


def test_confirmed_capability_syncs_to_knowledge_and_is_deduplicated(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    knowledge = FakeKnowledge()
    app.dependency_overrides[get_knowledge_client] = lambda: knowledge
    project = _create_project(client, auth_headers, tmp_path)
    project_id = UUID(str(project["id"]))
    note = _seed_note(
        session_factory,
        project_id=project_id,
        topic="登录重试",
        content="登录失败时最多重试三次。",
        tags=("auth",),
    )

    first = client.post(
        f"/api/capabilities/{note.id}/sync",
        headers=auth_headers,
        json={"project_id": str(project_id)},
    )
    assert first.status_code == 200, first.text
    payload = first.json()["data"]
    assert payload["deduplicated"] is False
    assert payload["document"]["source_path"] == f"capabilities/{note.id}.md"
    assert len(knowledge.uploads) == 1
    uploaded_content = knowledge.uploads[0][3].decode("utf-8")
    assert "登录重试" in uploaded_content
    assert "最多重试三次" in uploaded_content

    with UnitOfWork(session_factory) as uow:
        document = uow.documents.find_by_source_path(project_id, f"capabilities/{note.id}.md")
        assert document is not None
        assert document.external_document_id == "doc-1"
        assert document.content_hash == hashlib.sha256(knowledge.uploads[0][3]).hexdigest()

    second = client.post(
        f"/api/capabilities/{note.id}/sync",
        headers=auth_headers,
        json={"project_id": str(project_id)},
    )
    assert second.status_code == 200
    assert second.json()["data"]["deduplicated"] is True
    assert len(knowledge.uploads) == 1


def test_draft_capability_cannot_sync(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    knowledge = FakeKnowledge()
    app.dependency_overrides[get_knowledge_client] = lambda: knowledge
    project = _create_project(client, auth_headers, tmp_path)
    project_id = UUID(str(project["id"]))
    note = _seed_note(
        session_factory,
        project_id=project_id,
        topic="待确认能力",
        content="尚未确认",
        tags=("draft",),
        status=CapabilityStatus.DRAFT,
    )

    response = client.post(
        f"/api/capabilities/{note.id}/sync",
        headers=auth_headers,
        json={"project_id": str(project_id)},
    )

    assert response.status_code == 409
    assert knowledge.uploads == []
    with UnitOfWork(session_factory) as uow:
        assert uow.documents.list_by_project(project_id, PageRequest()).total == 0
