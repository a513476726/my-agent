from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderDataset:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class ProviderDocument:
    id: str
    dataset_id: str
    name: str


@dataclass(frozen=True, slots=True)
class ProviderHit:
    chunk_id: str
    document_id: str
    dataset_id: str
    title: str
    source_path: str
    snippet: str
    score: float
    page: int | None = None


class KnowledgeProvider(Protocol):
    async def find_dataset(self, name: str) -> ProviderDataset | None: ...

    async def create_dataset(self, name: str) -> ProviderDataset: ...

    async def upload_document(
        self,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> ProviderDocument: ...

    async def parse_documents(self, dataset_id: str, document_ids: tuple[str, ...]) -> None: ...

    async def delete_document(self, dataset_id: str, document_id: str) -> None: ...

    async def retrieve(
        self, dataset_id: str, question: str, top_k: int
    ) -> tuple[ProviderHit, ...]: ...
