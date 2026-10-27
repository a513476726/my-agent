from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from agent_api.dependencies import get_knowledge_client
from agent_api.knowledge import KnowledgeDataset, KnowledgeDocument
from agent_core import UnavailableError


class FakeKnowledgeClient:
    def __init__(self, *, fail_ensure: bool = False) -> None:
        self.fail_ensure = fail_ensure
        self.ensures: list[tuple[UUID, str]] = []
        self.uploads: list[tuple[UUID, str, str, bytes, str | None]] = []
        self._dataset_index = 0

    def ensure_dataset(self, project_id: UUID, name: str) -> KnowledgeDataset:
        if self.fail_ensure:
            raise UnavailableError("知识库服务不可用")
        self.ensures.append((project_id, name))
        self._dataset_index += 1
        return KnowledgeDataset(
            project_id=project_id,
            dataset_id=f"dataset-{self._dataset_index}",
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
        self.uploads.append((project_id, dataset_id, filename, content, content_type))
        return KnowledgeDocument(
            dataset_id=dataset_id,
            document_id=f"ragflow-doc-{len(self.uploads)}",
            filename=filename,
            parse_started=True,
        )

    def close(self) -> None:
        pass


@pytest.fixture
def knowledge_client() -> FakeKnowledgeClient:
    return FakeKnowledgeClient()


@pytest.fixture
def app_with_knowledge(app: object, knowledge_client: FakeKnowledgeClient) -> object:
    app.dependency_overrides[get_knowledge_client] = lambda: knowledge_client
    return app


@pytest.fixture
def ingest_client(app_with_knowledge: object) -> TestClient:
    with TestClient(app_with_knowledge) as test_client:
        yield test_client


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "test-password"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_project(client: TestClient, headers: dict[str, str], name: str) -> str:
    response = client.post(
        "/api/projects",
        headers=headers,
        json={"name": name, "path": f"/workspace/{name}", "vcs_type": "git"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


def _ingest(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    filename: str,
    content: bytes,
) -> dict[str, object]:
    response = client.post(
        "/api/documents/ingest",
        headers=headers,
        data={"project_id": project_id},
        files={"file": (filename, content, "text/markdown")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_ingest_creates_document_and_knowledge_mapping(
    ingest_client: TestClient, knowledge_client: FakeKnowledgeClient
) -> None:
    headers = _login(ingest_client)
    project_id = _create_project(ingest_client, headers, "项目 A")

    document = _ingest(ingest_client, headers, project_id, "需求.md", "## 登录\n密码登录".encode())

    assert document["deduplicated"] is False
    assert document["external_document_id"] == "ragflow-doc-1"
    assert document["knowledge_base_id"] is not None
    assert document["status"] == "pending"
    assert len(knowledge_client.ensures) == 1
    assert knowledge_client.uploads[0][:3] == (
        UUID(project_id),
        "dataset-1",
        "需求.md",
    )

    listing = ingest_client.get(f"/api/documents?project_id={project_id}", headers=headers)
    assert listing.json()["data"]["total"] == 1


def test_duplicate_content_with_different_path_is_skipped(
    ingest_client: TestClient, knowledge_client: FakeKnowledgeClient
) -> None:
    headers = _login(ingest_client)
    project_id = _create_project(ingest_client, headers, "项目 A")
    content = "同一份需求".encode()

    first = _ingest(ingest_client, headers, project_id, "需求.md", content)
    second = _ingest(ingest_client, headers, project_id, "副本/需求.md", content)

    assert first["id"] == second["id"]
    assert second["deduplicated"] is True
    assert len(knowledge_client.ensures) == 1
    assert len(knowledge_client.uploads) == 1

    listing = ingest_client.get(f"/api/documents?project_id={project_id}", headers=headers)
    assert listing.json()["data"]["total"] == 1


def test_same_content_in_different_projects_is_not_deduplicated(
    ingest_client: TestClient, knowledge_client: FakeKnowledgeClient
) -> None:
    headers = _login(ingest_client)
    project_a = _create_project(ingest_client, headers, "项目 A")
    project_b = _create_project(ingest_client, headers, "项目 B")

    first = _ingest(ingest_client, headers, project_a, "需求.md", b"same")
    second = _ingest(ingest_client, headers, project_b, "需求.md", b"same")

    assert first["id"] != second["id"]
    assert second["deduplicated"] is False
    assert [item[1] for item in knowledge_client.ensures] == ["项目 A", "项目 B"]
    assert [item[1] for item in knowledge_client.uploads] == ["dataset-1", "dataset-2"]


def test_ingest_maps_knowledge_outage_to_503_without_record(
    app: object, ingest_client: TestClient
) -> None:
    failing = FakeKnowledgeClient(fail_ensure=True)
    app.dependency_overrides[get_knowledge_client] = lambda: failing
    headers = _login(ingest_client)
    project_id = _create_project(ingest_client, headers, "项目 A")

    response = ingest_client.post(
        "/api/documents/ingest",
        headers=headers,
        data={"project_id": project_id},
        files={"file": ("需求.md", b"content", "text/markdown")},
    )

    assert response.status_code == 503
    assert response.json()["success"] is False
    listing = ingest_client.get(f"/api/documents?project_id={project_id}", headers=headers)
    assert listing.json()["data"]["total"] == 0


def test_ingest_rejects_empty_file(ingest_client: TestClient) -> None:
    headers = _login(ingest_client)
    project_id = _create_project(ingest_client, headers, "项目 A")

    response = ingest_client.post(
        "/api/documents/ingest",
        headers=headers,
        data={"project_id": project_id},
        files={"file": ("empty.md", b"", "text/markdown")},
    )

    assert response.status_code == 400
    assert response.json()["success"] is False


def test_ingest_rejects_unsupported_format_without_record(
    ingest_client: TestClient, knowledge_client: FakeKnowledgeClient
) -> None:
    headers = _login(ingest_client)
    project_id = _create_project(ingest_client, headers, "项目 A")

    response = ingest_client.post(
        "/api/documents/ingest",
        headers=headers,
        data={"project_id": project_id},
        files={"file": ("归档.zip", b"archive-bytes", "application/zip")},
    )

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert "不支持" in response.json()["message"]
    assert knowledge_client.ensures == []
    assert knowledge_client.uploads == []
    listing = ingest_client.get(f"/api/documents?project_id={project_id}", headers=headers)
    assert listing.json()["data"]["total"] == 0


def test_ingest_rejects_unknown_project(
    ingest_client: TestClient, knowledge_client: FakeKnowledgeClient
) -> None:
    headers = _login(ingest_client)

    response = ingest_client.post(
        "/api/documents/ingest",
        headers=headers,
        data={"project_id": "00000000-0000-0000-0000-000000000001"},
        files={"file": ("需求.md", b"content", "text/markdown")},
    )

    assert response.status_code == 404
    assert knowledge_client.ensures == []
