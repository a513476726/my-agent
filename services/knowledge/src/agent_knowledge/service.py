from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from uuid import UUID

from agent_core import is_supported_document_filename

from .errors import (
    DatasetNotConfiguredError,
    DatasetProjectMismatchError,
    KnowledgeValidationError,
)
from .provider import KnowledgeProvider, ProviderDataset, ProviderHit
from .schemas import RetrievalHitResponse, RetrievalResponse

_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
logger = logging.getLogger(__name__)


def dataset_name_for_project(project_id: UUID) -> str:
    return f"myagent-{project_id}"


def _normalize_source_path(value: str) -> str:
    path = value.replace("\\", "/").strip()
    return re.sub(r"^(?:\./)+", "", path)


def extract_heading_path(content: str) -> tuple[str, ...]:
    stack: list[tuple[int, str]] = []
    for line in content.splitlines():
        match = _HEADING_PATTERN.match(line.strip())
        if match is None:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        if title:
            stack.append((level, title))
    if not stack:
        return ("正文",)
    return tuple(title for _, title in stack)


@dataclass(frozen=True, slots=True)
class UploadedDocument:
    dataset_id: str
    document_id: str
    filename: str
    parse_started: bool


class DatasetMapper:
    def __init__(self, provider: KnowledgeProvider) -> None:
        self._provider = provider
        self._cache: dict[UUID, str] = {}
        self._locks: dict[UUID, asyncio.Lock] = {}

    async def ensure(self, project_id: UUID, display_name: str) -> ProviderDataset:
        lock = self._locks.setdefault(project_id, asyncio.Lock())
        async with lock:
            cached = self._cache.get(project_id)
            if cached is not None:
                return ProviderDataset(id=cached, name=dataset_name_for_project(project_id))
            stable_name = dataset_name_for_project(project_id)
            dataset = await self._provider.find_dataset(stable_name)
            if dataset is None:
                dataset = await self._provider.create_dataset(stable_name)
            self._cache[project_id] = dataset.id
            return dataset

    async def resolve(self, project_id: UUID) -> str:
        cached = self._cache.get(project_id)
        if cached is not None:
            return cached
        dataset = await self._provider.find_dataset(dataset_name_for_project(project_id))
        if dataset is None:
            raise DatasetNotConfiguredError("项目尚未配置知识库数据集")
        self._cache[project_id] = dataset.id
        return dataset.id


class KnowledgeGatewayService:
    def __init__(self, provider: KnowledgeProvider) -> None:
        self._provider = provider
        self._mapper = DatasetMapper(provider)

    async def ensure_dataset(self, project_id: UUID, name: str) -> ProviderDataset:
        return await self._mapper.ensure(project_id, name)

    async def upload_document(
        self,
        *,
        project_id: UUID,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
        parse: bool,
    ) -> UploadedDocument:
        if not filename.strip():
            raise KnowledgeValidationError("filename 不能为空")
        if not content:
            raise KnowledgeValidationError("文件内容不能为空")
        if not is_supported_document_filename(filename):
            raise KnowledgeValidationError("不支持的文件格式")
        expected = await self._mapper.resolve(project_id)
        if expected != dataset_id:
            raise DatasetProjectMismatchError("项目与数据集不匹配")
        document = await self._provider.upload_document(dataset_id, filename, content, content_type)
        if document.dataset_id != dataset_id:
            raise DatasetProjectMismatchError("上游返回了不属于该数据集的文档")
        if parse:
            try:
                await self._provider.parse_documents(dataset_id, (document.id,))
            except Exception:
                try:
                    await self._provider.delete_document(dataset_id, document.id)
                except Exception:
                    logger.exception("解析失败后回滚 RAGFlow 文档失败")
                raise
        return UploadedDocument(
            dataset_id=dataset_id,
            document_id=document.id,
            filename=document.name,
            parse_started=parse,
        )

    async def retrieve(self, *, project_id: UUID, query: str, top_k: int) -> RetrievalResponse:
        dataset_id = await self._mapper.resolve(project_id)
        provider_hits = await self._provider.retrieve(dataset_id, query, top_k)
        normalized = [
            self._normalize_hit(hit, dataset_id)
            for hit in provider_hits
            if hit.dataset_id == dataset_id
        ][:top_k]
        return RetrievalResponse(hits=normalized, total=len(normalized), matched=bool(normalized))

    async def delete_document(self, *, project_id: UUID, dataset_id: str, document_id: str) -> None:
        if not document_id.strip():
            raise KnowledgeValidationError("document_id 不能为空")
        expected = await self._mapper.resolve(project_id)
        if expected != dataset_id:
            raise DatasetProjectMismatchError("项目与数据集不匹配")
        await self._provider.delete_document(dataset_id, document_id)

    @staticmethod
    def _normalize_hit(hit: ProviderHit, dataset_id: str) -> RetrievalHitResponse:
        source_path = _normalize_source_path(hit.source_path) or _normalize_source_path(hit.title)
        return RetrievalHitResponse(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            title=hit.title,
            source_path=source_path,
            heading_path=list(extract_heading_path(hit.snippet)),
            snippet=hit.snippet,
            score=max(0.0, hit.score),
            page=hit.page,
        )
