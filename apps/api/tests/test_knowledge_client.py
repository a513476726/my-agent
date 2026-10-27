from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest

from agent_api.knowledge import KnowledgeClient
from agent_core import DomainValidationError, NotFoundError, UnavailableError


def _client(handler: httpx.MockTransport) -> KnowledgeClient:
    return KnowledgeClient(
        base_url="http://knowledge.test",
        timeout_seconds=5,
        client=httpx.Client(base_url="http://knowledge.test", transport=handler),
    )


def test_ensure_dataset_uses_gateway_contract() -> None:
    project_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/datasets"
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


def test_upload_document_uses_multipart_and_returns_external_id() -> None:
    project_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/datasets/dataset-1/documents"
        body = request.content
        assert str(project_id).encode() in body
        assert 'filename="需求.md"'.encode() in body
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


def test_gateway_error_maps_to_domain_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"code": 400, "data": None, "message": "项目参数无效", "success": False},
        )

    with pytest.raises(DomainValidationError, match="项目参数无效"):
        _client(httpx.MockTransport(handler)).ensure_dataset(uuid4(), "项目 A")


def test_gateway_not_found_maps_to_domain_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "code": 404,
                "data": None,
                "message": "项目尚未配置知识库数据集",
                "success": False,
            },
        )

    with pytest.raises(NotFoundError, match="项目尚未配置知识库数据集"):
        _client(httpx.MockTransport(handler)).ensure_dataset(uuid4(), "项目 A")


def test_gateway_outage_maps_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(UnavailableError, match="知识库服务不可用"):
        _client(httpx.MockTransport(handler)).ensure_dataset(uuid4(), "项目 A")
