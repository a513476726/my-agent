from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from agent_knowledge.app import create_app
from agent_knowledge.errors import (
    DatasetProjectMismatchError,
    KnowledgeUnavailableError,
    KnowledgeUpstreamError,
)
from agent_knowledge.provider import ProviderDataset, ProviderDocument, ProviderHit


class FakeProvider:
    def __init__(self) -> None:
        self.datasets: dict[str, ProviderDataset] = {}
        self.uploads: list[dict[str, object]] = []
        self.parsed: list[tuple[str, tuple[str, ...]]] = []
        self.deleted: list[tuple[str, str]] = []
        self.retrievals: list[tuple[str, str, int]] = []
        self.hits_by_dataset: dict[str, list[ProviderHit]] = {}
        self.parse_error: Exception | None = None
        self.delete_error: Exception | None = None
        self.retrieve_error: Exception | None = None
        self._next_dataset = 1

    async def find_dataset(self, name: str) -> ProviderDataset | None:
        return self.datasets.get(name)

    async def create_dataset(self, name: str) -> ProviderDataset:
        dataset = ProviderDataset(id=f"dataset-{self._next_dataset}", name=name)
        self._next_dataset += 1
        self.datasets[name] = dataset
        return dataset

    async def upload_document(
        self,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> ProviderDocument:
        self.uploads.append(
            {
                "dataset_id": dataset_id,
                "filename": filename,
                "content": content,
                "content_type": content_type,
            }
        )
        return ProviderDocument(
            id=f"document-{len(self.uploads)}",
            dataset_id=dataset_id,
            name=filename,
        )

    async def parse_documents(self, dataset_id: str, document_ids: tuple[str, ...]) -> None:
        self.parsed.append((dataset_id, document_ids))
        if self.parse_error is not None:
            raise self.parse_error

    async def delete_document(self, dataset_id: str, document_id: str) -> None:
        self.deleted.append((dataset_id, document_id))
        if self.delete_error is not None:
            raise self.delete_error

    async def retrieve(self, dataset_id: str, question: str, top_k: int) -> tuple[ProviderHit, ...]:
        self.retrievals.append((dataset_id, question, top_k))
        if self.retrieve_error is not None:
            raise self.retrieve_error
        return tuple(self.hits_by_dataset.get(dataset_id, ()))


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def client(provider: FakeProvider) -> Iterator[TestClient]:
    with TestClient(create_app(provider=provider)) as test_client:
        yield test_client


def _ensure_dataset(client: TestClient, project_id: UUID, name: str = "项目 A") -> str:
    response = client.post(
        "/v1/datasets",
        json={"project_id": str(project_id), "name": name},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["dataset_id"]


def test_create_dataset_is_idempotent(client: TestClient, provider: FakeProvider) -> None:
    project_id = uuid4()

    first = _ensure_dataset(client, project_id)
    second = _ensure_dataset(client, project_id)

    assert first == second
    assert len(provider.datasets) == 1
    assert next(iter(provider.datasets)) == f"myagent-{project_id}"


def test_upload_document_uses_dataset_and_starts_parsing(
    client: TestClient, provider: FakeProvider
) -> None:
    project_id = uuid4()
    dataset_id = _ensure_dataset(client, project_id)

    response = client.post(
        f"/v1/datasets/{dataset_id}/documents",
        data={"project_id": str(project_id), "parse": "true"},
        files={"file": ("需求.md", "## 登录\n必须支持密码登录".encode(), "text/markdown")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["data"]["document_id"] == "document-1"
    assert provider.uploads[0]["dataset_id"] == dataset_id
    assert provider.uploads[0]["content"] == "## 登录\n必须支持密码登录".encode()
    assert provider.parsed == [(dataset_id, ("document-1",))]


def test_upload_rejects_dataset_from_another_project(
    client: TestClient, provider: FakeProvider
) -> None:
    project_a = uuid4()
    project_b = uuid4()
    dataset_a = _ensure_dataset(client, project_a, "项目 A")
    _ensure_dataset(client, project_b, "项目 B")

    response = client.post(
        f"/v1/datasets/{dataset_a}/documents",
        data={"project_id": str(project_b), "parse": "true"},
        files={"file": ("需求.md", b"content", "text/markdown")},
    )

    assert response.status_code == 404
    assert response.json()["success"] is False
    assert provider.uploads == []


def test_upload_rejects_unsupported_format_without_half_record(
    client: TestClient, provider: FakeProvider
) -> None:
    project_id = uuid4()
    dataset_id = _ensure_dataset(client, project_id)

    response = client.post(
        f"/v1/datasets/{dataset_id}/documents",
        data={"project_id": str(project_id), "parse": "true"},
        files={"file": ("归档.zip", b"not-a-document", "application/zip")},
    )

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert "不支持" in response.json()["message"]
    assert provider.uploads == []
    assert provider.parsed == []


def test_parse_failure_removes_uploaded_document(
    client: TestClient, provider: FakeProvider
) -> None:
    project_id = uuid4()
    dataset_id = _ensure_dataset(client, project_id)
    provider.parse_error = KnowledgeUpstreamError("解析启动失败")

    response = client.post(
        f"/v1/datasets/{dataset_id}/documents",
        data={"project_id": str(project_id), "parse": "true"},
        files={"file": ("需求.md", b"content", "text/markdown")},
    )

    assert response.status_code == 502
    assert response.json()["message"] == "解析启动失败"
    assert provider.deleted == [(dataset_id, "document-1")]


def test_parse_failure_still_returns_original_error_when_cleanup_fails(
    client: TestClient, provider: FakeProvider
) -> None:
    project_id = uuid4()
    dataset_id = _ensure_dataset(client, project_id)
    provider.parse_error = KnowledgeUpstreamError("解析启动失败")
    provider.delete_error = KnowledgeUpstreamError("回滚失败")

    response = client.post(
        f"/v1/datasets/{dataset_id}/documents",
        data={"project_id": str(project_id), "parse": "true"},
        files={"file": ("需求.md", b"content", "text/markdown")},
    )

    assert response.status_code == 502
    assert response.json()["message"] == "解析启动失败"
    assert provider.deleted == [(dataset_id, "document-1")]


def test_retrieval_normalizes_source_heading_score_and_page(
    client: TestClient, provider: FakeProvider
) -> None:
    project_id = uuid4()
    dataset_id = _ensure_dataset(client, project_id)
    provider.hits_by_dataset[dataset_id] = [
        ProviderHit(
            chunk_id="chunk-1",
            document_id="ragflow-doc-1",
            dataset_id=dataset_id,
            title="需求.md",
            source_path="docs\\需求.md",
            snippet="# 登录\n## 密码规则\n密码至少 12 位",
            score=0.91,
            page=3,
        )
    ]

    response = client.post(
        "/v1/retrieval",
        json={"project_id": str(project_id), "query": "密码规则", "top_k": 5},
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["total"] == 1
    assert body["matched"] is True
    assert body["hits"][0] == {
        "chunk_id": "chunk-1",
        "document_id": "ragflow-doc-1",
        "title": "需求.md",
        "source_path": "docs/需求.md",
        "heading_path": ["登录", "密码规则"],
        "snippet": "# 登录\n## 密码规则\n密码至少 12 位",
        "score": 0.91,
        "page": 3,
    }
    assert provider.retrievals == [(dataset_id, "密码规则", 5)]


def test_retrieval_filters_hits_from_other_datasets(
    client: TestClient, provider: FakeProvider
) -> None:
    project_id = uuid4()
    dataset_id = _ensure_dataset(client, project_id)
    foreign = ProviderHit(
        chunk_id="chunk-foreign",
        document_id="foreign-doc",
        dataset_id="dataset-other",
        title="别的项目.md",
        source_path="别的项目.md",
        snippet="不应出现",
        score=0.99,
    )
    provider.hits_by_dataset[dataset_id] = [foreign]

    response = client.post(
        "/v1/retrieval",
        json={"project_id": str(project_id), "query": "任何词"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {"hits": [], "total": 0, "matched": False}


def test_projects_retrieve_only_their_own_dataset(
    client: TestClient, provider: FakeProvider
) -> None:
    project_a, project_b = uuid4(), uuid4()
    dataset_a = _ensure_dataset(client, project_a, "项目 A")
    dataset_b = _ensure_dataset(client, project_b, "项目 B")
    provider.hits_by_dataset[dataset_a] = [
        ProviderHit(
            chunk_id="a",
            document_id="doc-a",
            dataset_id=dataset_a,
            title="A.md",
            source_path="A.md",
            snippet="A",
            score=0.8,
        )
    ]
    provider.hits_by_dataset[dataset_b] = [
        ProviderHit(
            chunk_id="b",
            document_id="doc-b",
            dataset_id=dataset_b,
            title="B.md",
            source_path="B.md",
            snippet="B",
            score=0.8,
        )
    ]

    result_a = client.post("/v1/retrieval", json={"project_id": str(project_a), "query": "内容"})
    result_b = client.post("/v1/retrieval", json={"project_id": str(project_b), "query": "内容"})

    assert result_a.json()["data"]["hits"][0]["document_id"] == "doc-a"
    assert result_b.json()["data"]["hits"][0]["document_id"] == "doc-b"
    assert [item[0] for item in provider.retrievals] == [dataset_a, dataset_b]


def test_delete_document_resolves_dataset_and_delegates(
    client: TestClient, provider: FakeProvider
) -> None:
    project_id = uuid4()
    dataset_id = _ensure_dataset(client, project_id)

    response = client.delete(
        f"/v1/datasets/{dataset_id}/documents/document-1",
        params={"project_id": str(project_id)},
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {"deleted": True}
    assert provider.deleted == [(dataset_id, "document-1")]


def test_delete_document_rejects_dataset_from_other_project(
    client: TestClient, provider: FakeProvider
) -> None:
    project_id = uuid4()
    dataset_id = _ensure_dataset(client, project_id)
    other_project = uuid4()
    _ensure_dataset(client, other_project, "项目 B")

    response = client.delete(
        f"/v1/datasets/{dataset_id}/documents/document-1",
        params={"project_id": str(other_project)},
    )

    assert response.status_code == 404
    assert provider.deleted == []


def test_retrieval_without_dataset_returns_not_found(client: TestClient) -> None:
    response = client.post(
        "/v1/retrieval",
        json={"project_id": str(uuid4()), "query": "内容"},
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_retrieval_maps_provider_outage_to_503(client: TestClient, provider: FakeProvider) -> None:
    project_id = uuid4()
    _ensure_dataset(client, project_id)
    provider.retrieve_error = KnowledgeUnavailableError("知识库服务不可用")

    response = client.post(
        "/v1/retrieval",
        json={"project_id": str(project_id), "query": "内容"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "code": 503,
        "data": None,
        "message": "知识库服务不可用",
        "success": False,
    }


def test_retrieval_validation_uses_envelope(client: TestClient) -> None:
    response = client.post(
        "/v1/retrieval",
        json={"project_id": str(uuid4()), "query": " ", "top_k": 0},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["code"] == 422


def test_mismatch_error_type_is_stable() -> None:
    error = DatasetProjectMismatchError("项目与数据集不匹配")
    assert error.message == "项目与数据集不匹配"
