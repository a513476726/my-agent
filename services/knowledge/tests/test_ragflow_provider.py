from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

import httpx
import pytest

from agent_knowledge.errors import KnowledgeUnavailableError, KnowledgeUpstreamError
from agent_knowledge.ragflow import RAGFlowProvider

Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


def _run(provider: RAGFlowProvider, action: str, *args: object) -> object:
    return asyncio.run(getattr(provider, action)(*args))


def _provider(handler: Handler) -> RAGFlowProvider:
    client = httpx.AsyncClient(
        base_url="http://ragflow.test",
        transport=httpx.MockTransport(handler),
    )
    return RAGFlowProvider(
        base_url="http://ragflow.test",
        api_key="test-api-key",
        timeout_seconds=5,
        client=client,
    )


@pytest.mark.parametrize("name", ["myagent-abc", "项目 A"])
def test_create_dataset_uses_builtin_general_parser_and_bearer_auth(name: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/datasets"
        assert request.headers["Authorization"] == "Bearer test-api-key"
        payload = json.loads(request.content)
        assert payload == {
            "name": name,
            "language": "Chinese",
            "parse_type": 1,
            "parser_id": "general",
        }
        return httpx.Response(200, json={"code": 0, "data": {"id": "ds-1", "name": name}})

    dataset = _run(_provider(handler), "create_dataset", name)

    assert dataset.id == "ds-1"
    assert dataset.name == name


def test_create_dataset_includes_configured_embedding_model() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["embedding_model"] == "BAAI/bge-m3@BAAI"
        return httpx.Response(200, json={"code": 0, "data": {"id": "ds-1", "name": "kb"}})

    client = httpx.AsyncClient(
        base_url="http://ragflow.test",
        transport=httpx.MockTransport(handler),
    )
    provider = RAGFlowProvider(
        base_url="http://ragflow.test",
        api_key="test-api-key",
        timeout_seconds=5,
        embedding_model="BAAI/bge-m3@BAAI",
        client=client,
    )

    asyncio.run(provider.create_dataset("kb"))


def test_find_dataset_matches_exact_name() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/datasets"
        assert request.url.params["name"] == "myagent-abc"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": [
                    {"id": "other", "name": "myagent-abc-old"},
                    {"id": "ds-1", "name": "myagent-abc"},
                ],
            },
        )

    dataset = _run(_provider(handler), "find_dataset", "myagent-abc")

    assert dataset is not None
    assert dataset.id == "ds-1"


def test_find_dataset_returns_none_when_not_found() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0, "data": []})

    assert _run(_provider(handler), "find_dataset", "missing") is None


def test_upload_and_parse_document_shapes() -> None:
    state: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/datasets/ds-1/documents":
            assert request.method == "POST"
            body = await request.aread()
            assert 'filename="需求.md"'.encode() in body
            assert "必须支持密码登录".encode() in body
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": [
                        {
                            "id": "doc-1",
                            "dataset_id": "ds-1",
                            "name": "需求.md",
                        }
                    ],
                },
            )
        if request.url.path == "/api/v1/datasets/ds-1/chunks":
            state["parse"] = json.loads(request.content)
            return httpx.Response(200, json={"code": 0})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = _provider(handler)
    document = asyncio.run(
        provider.upload_document(
            "ds-1",
            "需求.md",
            "## 登录\n必须支持密码登录".encode(),
            "text/markdown",
        )
    )
    asyncio.run(provider.parse_documents("ds-1", (document.id,)))

    assert document.id == "doc-1"
    assert state["parse"] == {"document_ids": ["doc-1"]}


def test_delete_document_uses_bulk_ids_shape() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/api/v1/datasets/ds-1/documents"
        assert json.loads(request.content) == {"ids": ["doc-1"]}
        return httpx.Response(200, json={"code": 0, "data": {}})

    asyncio.run(_provider(handler).delete_document("ds-1", "doc-1"))


def test_retrieve_normalizes_ragflow_chunks() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/retrieval"
        payload = json.loads(request.content)
        assert payload["question"] == "密码规则"
        assert payload["dataset_ids"] == ["ds-1"]
        assert payload["page_size"] == 5
        assert payload["include_knowledge_compilation"] is False
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "chunks": [
                        {
                            "id": "chunk-1",
                            "content": "# 登录\n## 密码规则\n密码至少 12 位",
                            "document_id": "doc-1",
                            "document_keyword": "docs\\需求.md",
                            "dataset_id": "ds-1",
                            "positions": [[7, 0, 0, 0, 0]],
                            "similarity": 0.88,
                        }
                    ],
                    "total": 1,
                },
            },
        )

    hits = _run(_provider(handler), "retrieve", "ds-1", "密码规则", 5)

    assert len(hits) == 1
    assert hits[0].source_path == "docs/需求.md"
    assert hits[0].page == 7
    assert hits[0].score == 0.88


def test_ragflow_error_code_becomes_upstream_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 102, "message": "dataset 不存在"})

    with pytest.raises(KnowledgeUpstreamError, match="dataset 不存在"):
        _run(_provider(handler), "find_dataset", "missing")


def test_ragflow_timeout_becomes_unavailable_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(KnowledgeUnavailableError, match="知识库服务不可用"):
        _run(_provider(handler), "find_dataset", "missing")
