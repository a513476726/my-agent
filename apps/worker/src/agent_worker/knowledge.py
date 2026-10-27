from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx

from agent_core import DomainValidationError, NotFoundError, UnavailableError


@dataclass(frozen=True, slots=True)
class KnowledgeDataset:
    project_id: UUID
    dataset_id: str
    name: str


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    dataset_id: str
    document_id: str
    filename: str
    parse_started: bool


class KnowledgeClient(Protocol):
    def ensure_dataset(self, project_id: UUID, name: str) -> KnowledgeDataset: ...

    def upload_document(
        self,
        project_id: UUID,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> KnowledgeDocument: ...

    def delete_document(self, project_id: UUID, dataset_id: str, document_id: str) -> None: ...


class HttpKnowledgeClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = client is None
        self._timeout = httpx.Timeout(timeout_seconds)
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=self._timeout,
        )

    def __enter__(self) -> HttpKnowledgeClient:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def ensure_dataset(self, project_id: UUID, name: str) -> KnowledgeDataset:
        data = self._request(
            "POST",
            "/v1/datasets",
            json={"project_id": str(project_id), "name": name},
        )
        return KnowledgeDataset(
            project_id=UUID(str(data["project_id"])),
            dataset_id=str(data["dataset_id"]),
            name=str(data["name"]),
        )

    def upload_document(
        self,
        project_id: UUID,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> KnowledgeDocument:
        data = self._request(
            "POST",
            f"/v1/datasets/{dataset_id}/documents",
            data={"project_id": str(project_id), "parse": "true"},
            files={
                "file": (
                    filename,
                    content,
                    content_type or "application/octet-stream",
                )
            },
        )
        return KnowledgeDocument(
            dataset_id=str(data["dataset_id"]),
            document_id=str(data["document_id"]),
            filename=str(data["filename"]),
            parse_started=bool(data["parse_started"]),
        )

    def delete_document(self, project_id: UUID, dataset_id: str, document_id: str) -> None:
        self._request(
            "DELETE",
            f"/v1/datasets/{dataset_id}/documents/{document_id}",
            params={"project_id": str(project_id)},
        )

    def _request(self, method: str, path: str, **kwargs: object) -> dict[str, object]:
        try:
            response = self._client.request(method, path, timeout=self._timeout, **kwargs)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise UnavailableError("知识库服务不可用") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise UnavailableError("知识库服务返回了无效响应") from exc
        if not isinstance(payload, dict):
            raise UnavailableError("知识库服务返回了无效响应")
        message = str(payload.get("message", "知识库服务不可用"))
        if response.status_code >= 500:
            raise UnavailableError(message)
        if response.status_code == 404:
            raise NotFoundError(message)
        if response.status_code >= 400 or payload.get("success") is not True:
            raise DomainValidationError(message)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise UnavailableError("知识库服务返回了无效响应")
        return data
