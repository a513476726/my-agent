from __future__ import annotations

import re
from typing import Any

import httpx

from .errors import (
    KnowledgeUnavailableError,
    KnowledgeUpstreamError,
)
from .provider import ProviderDataset, ProviderDocument, ProviderHit


def _normalize_source_path(value: str) -> str:
    path = value.replace("\\", "/").strip()
    return re.sub(r"^(?:\./)+", "", path)


def _extract_page(positions: object) -> int | None:
    if not isinstance(positions, list) or not positions:
        return None
    first = positions[0]
    if isinstance(first, list) and first and isinstance(first[0], int) and first[0] > 0:
        return first[0]
    if isinstance(first, int) and first > 0:
        return first
    if isinstance(first, str):
        match = re.search(r"\d+", first)
        if match and int(match.group()) > 0:
            return int(match.group())
    return None


class RAGFlowProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        embedding_model: str = "",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._embedding_model = embedding_model.strip()
        self._owns_client = client is None
        self._timeout = httpx.Timeout(timeout_seconds)
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=self._timeout,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def find_dataset(self, name: str) -> ProviderDataset | None:
        data = await self._request(
            "GET",
            "/api/v1/datasets",
            params={"page": 1, "page_size": 100, "name": name},
        )
        if not isinstance(data, list):
            raise KnowledgeUpstreamError("RAGFlow 数据集列表格式无效")
        for item in data:
            if (
                not isinstance(item, dict)
                or str(item.get("name", "")).casefold() != name.casefold()
            ):
                continue
            dataset_id = str(item.get("id", "")).strip()
            if dataset_id:
                return ProviderDataset(id=dataset_id, name=str(item.get("name", name)))
        return None

    async def create_dataset(self, name: str) -> ProviderDataset:
        payload: dict[str, object] = {
            "name": name,
            "language": "Chinese",
            "parse_type": 1,
            "parser_id": "general",
        }
        if self._embedding_model:
            payload["embedding_model"] = self._embedding_model
        data = await self._request("POST", "/api/v1/datasets", json=payload)
        if not isinstance(data, dict):
            raise KnowledgeUpstreamError("RAGFlow 创建数据集响应格式无效")
        dataset_id = str(data.get("id", "")).strip()
        if not dataset_id:
            raise KnowledgeUpstreamError("RAGFlow 未返回数据集标识")
        return ProviderDataset(id=dataset_id, name=str(data.get("name", name)))

    async def upload_document(
        self,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> ProviderDocument:
        data = await self._request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/documents",
            files={
                "file": (
                    filename,
                    content,
                    content_type or "application/octet-stream",
                )
            },
        )
        rows = data if isinstance(data, list) else [data]
        for row in rows:
            if not isinstance(row, dict):
                continue
            document_id = str(row.get("id", "")).strip()
            if document_id:
                return ProviderDocument(
                    id=document_id,
                    dataset_id=str(row.get("dataset_id", dataset_id)),
                    name=str(row.get("name", filename)),
                )
        raise KnowledgeUpstreamError("RAGFlow 未返回文档标识")

    async def parse_documents(self, dataset_id: str, document_ids: tuple[str, ...]) -> None:
        await self._request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/chunks",
            json={"document_ids": list(document_ids)},
        )

    async def delete_document(self, dataset_id: str, document_id: str) -> None:
        await self._request(
            "DELETE",
            f"/api/v1/datasets/{dataset_id}/documents",
            json={"ids": [document_id]},
        )

    async def retrieve(self, dataset_id: str, question: str, top_k: int) -> tuple[ProviderHit, ...]:
        data = await self._request(
            "POST",
            "/api/v1/retrieval",
            json={
                "question": question,
                "dataset_ids": [dataset_id],
                "page_size": top_k,
                "knn_top_k": max(128, top_k * 8),
                "include_knowledge_compilation": False,
            },
        )
        if not isinstance(data, dict):
            raise KnowledgeUpstreamError("RAGFlow 检索响应格式无效")
        chunks = data.get("chunks", [])
        if not isinstance(chunks, list):
            raise KnowledgeUpstreamError("RAGFlow 检索结果格式无效")
        hits: list[ProviderHit] = []
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            snippet = str(chunk.get("content", "")).strip()
            document_id = str(chunk.get("document_id", "")).strip()
            if not snippet or not document_id:
                continue
            title = str(chunk.get("document_keyword", "")).strip() or document_id
            source_path = _normalize_source_path(str(chunk.get("location", "")).strip())
            source_path = source_path or _normalize_source_path(title)
            raw_score = chunk.get("similarity", 0.0)
            try:
                score = max(0.0, float(raw_score))
            except (TypeError, ValueError):
                score = 0.0
            hits.append(
                ProviderHit(
                    chunk_id=str(chunk.get("id", "")).strip(),
                    document_id=document_id,
                    dataset_id=str(chunk.get("dataset_id", "")).strip(),
                    title=title,
                    source_path=source_path,
                    snippet=snippet,
                    score=score,
                    page=_extract_page(chunk.get("positions")),
                )
            )
        return tuple(hits)

    async def _request(self, method: str, path: str, **kwargs: Any) -> object:
        if not self._api_key:
            raise KnowledgeUnavailableError("未配置 RAGFLOW_API_KEY")
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = await self._client.request(
                method,
                path,
                headers=headers,
                timeout=self._timeout,
                **kwargs,
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise KnowledgeUnavailableError("知识库服务不可用") from exc

        if response.status_code >= 500:
            raise KnowledgeUnavailableError("知识库服务不可用")
        if response.status_code >= 400:
            raise KnowledgeUpstreamError(f"RAGFlow 请求失败（HTTP {response.status_code}）")
        try:
            payload = response.json()
        except ValueError as exc:
            raise KnowledgeUpstreamError("RAGFlow 返回了非 JSON 响应") from exc
        if not isinstance(payload, dict):
            raise KnowledgeUpstreamError("RAGFlow 响应格式无效")
        code = payload.get("code", 0)
        if code not in (0, "0", None):
            message = str(payload.get("message", "RAGFlow 返回错误"))[:500]
            raise KnowledgeUpstreamError(message)
        return payload.get("data")
