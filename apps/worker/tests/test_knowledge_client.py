from __future__ import annotations

import json
from uuid import uuid4

import httpx

from agent_worker.knowledge import HttpKnowledgeClient


def _client(handler: httpx.MockTransport) -> HttpKnowledgeClient:
    return HttpKnowledgeClient(
        base_url="http://knowledge.test",
        timeout_seconds=5,
        client=httpx.Client(base_url="http://knowledge.test", transport=handler),
    )


def test_upload_document_uses_gateway_contract() -> None:
    project_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/datasets/dataset-1/documents"
        assert str(project_id).encode() in request.content
        assert 'filename="需求.md"'.encode() in request.content
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "dataset_id": "dataset-1",
                    "document_id": "ragflow-doc-1",
                    "filename": "需求.md",
                    "parse_started": True,
                },
                "message": "ok",
                "success": True,
            },
        )

    document = _client(httpx.MockTransport(handler)).upload_document(
        project_id,
        "dataset-1",
        "需求.md",
        b"content",
        "text/markdown",
    )

    assert document.document_id == "ragflow-doc-1"
    assert document.parse_started is True


def test_delete_document_uses_project_scoped_endpoint() -> None:
    project_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/v1/datasets/dataset-1/documents/document-1"
        assert request.url.params["project_id"] == str(project_id)
        return httpx.Response(
            200,
            json={"code": 0, "data": {"deleted": True}, "message": "ok", "success": True},
        )

    _client(httpx.MockTransport(handler)).delete_document(project_id, "dataset-1", "document-1")


def test_ensure_dataset_returns_gateway_identity() -> None:
    project_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {
            "project_id": str(project_id),
            "name": "项目 A",
        }
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "project_id": str(project_id),
                    "dataset_id": "dataset-1",
                    "name": "myagent-project",
                },
                "message": "ok",
                "success": True,
            },
        )

    dataset = _client(httpx.MockTransport(handler)).ensure_dataset(project_id, "项目 A")

    assert dataset.dataset_id == "dataset-1"
    assert dataset.project_id == project_id
