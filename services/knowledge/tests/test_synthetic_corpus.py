from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from fastapi.testclient import TestClient

from agent_knowledge.app import create_app
from agent_knowledge.provider import ProviderDataset, ProviderDocument, ProviderHit


@dataclass(frozen=True, slots=True)
class SyntheticDocument:
    filename: str
    source_path: str
    marker: str
    content: str
    category: str
    heading_path: tuple[str, str]
    page: int | None = None


class SyntheticCorpusProvider:
    """内存 Provider：只验证网关契约，不冒充 RAGFlow 的真实解析质量。"""

    def __init__(self, corpus: tuple[SyntheticDocument, ...]) -> None:
        self._corpus = {document.filename: document for document in corpus}
        self.datasets: dict[str, ProviderDataset] = {}
        self.documents_by_dataset: dict[str, list[SyntheticDocument]] = {}
        self.uploads: list[dict[str, object]] = []
        self.parsed: list[tuple[str, tuple[str, ...]]] = []
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
        document = self._corpus[filename]
        self.uploads.append(
            {
                "dataset_id": dataset_id,
                "filename": filename,
                "content": content,
                "content_type": content_type,
            }
        )
        self.documents_by_dataset.setdefault(dataset_id, []).append(document)
        return ProviderDocument(
            id=f"document-{len(self.uploads)}",
            dataset_id=dataset_id,
            name=filename,
        )

    async def parse_documents(self, dataset_id: str, document_ids: tuple[str, ...]) -> None:
        self.parsed.append((dataset_id, document_ids))

    async def delete_document(self, dataset_id: str, document_id: str) -> None:
        return None

    async def retrieve(self, dataset_id: str, question: str, top_k: int) -> tuple[ProviderHit, ...]:
        hits = [
            ProviderHit(
                chunk_id=f"chunk-{document.marker}",
                document_id=f"document-{document.marker}",
                dataset_id=dataset_id,
                title=document.filename,
                source_path=document.source_path,
                snippet=document.content,
                score=0.99,
                page=document.page,
            )
            for document in self.documents_by_dataset.get(dataset_id, ())
            if question == document.marker
        ]
        return tuple(hits[:top_k])


def _build_synthetic_corpus() -> tuple[SyntheticDocument, ...]:
    documents: list[SyntheticDocument] = []

    for index in range(1, 16):
        marker = f"SYN-TEXT-{index:02d}"
        documents.append(
            SyntheticDocument(
                filename=f"需求说明-{index:02d}.md",
                source_path=f"docs/requirements/需求说明-{index:02d}.md",
                marker=marker,
                content=(
                    f"# 需求说明 {index:02d}\n\n"
                    f"## 业务规则 {index:02d}\n\n"
                    f"{marker}：该文档描述登录、权限与重试策略中的第 {index} 组验收条件。"
                ),
                category="markdown",
                heading_path=(f"需求说明 {index:02d}", f"业务规则 {index:02d}"),
            )
        )

    for index, page in enumerate((2, 7, 11), start=1):
        marker = f"SYN-SCAN-{index:02d}"
        documents.append(
            SyntheticDocument(
                filename=f"扫描合同-{index:02d}.pdf",
                source_path=f"docs/scans/扫描合同-{index:02d}.pdf",
                marker=marker,
                content=(
                    f"# 扫描合同 {index:02d}\n\n"
                    f"## 第 {page} 页\n\n"
                    f"{marker}：扫描件 OCR 文本，包含签署日期、付款节点与验收条款。"
                ),
                category="scanned_pdf",
                heading_path=(f"扫描合同 {index:02d}", f"第 {page} 页"),
                page=page,
            )
        )

    for index in range(1, 3):
        marker = f"SYN-TABLE-{index:02d}"
        documents.append(
            SyntheticDocument(
                filename=f"复杂表格-{index:02d}.xlsx",
                source_path=f"docs/tables/复杂表格-{index:02d}.xlsx",
                marker=marker,
                content=(
                    f"# 折扣矩阵 {index:02d}\n\n"
                    f"## 区域价格表 {index:02d}\n\n"
                    f"{marker}\n\n"
                    "| 区域 | 折扣 | 最低采购量 |\n"
                    "| --- | --- | --- |\n"
                    f"| 华东-{index} | 0.92 | 100 |\n"
                    f"| 华南-{index} | 0.95 | 200 |"
                ),
                category="complex_table",
                heading_path=(f"折扣矩阵 {index:02d}", f"区域价格表 {index:02d}"),
            )
        )

    return tuple(documents)


def test_twenty_document_synthetic_corpus_acceptance() -> None:
    corpus = _build_synthetic_corpus()
    assert len(corpus) == 20
    assert sum(document.category == "scanned_pdf" for document in corpus) >= 2
    assert sum(document.category == "complex_table" for document in corpus) >= 2

    provider = SyntheticCorpusProvider(corpus)
    with TestClient(create_app(provider=provider)) as client:
        project_id = uuid4()
        dataset_response = client.post(
            "/v1/datasets",
            json={"project_id": str(project_id), "name": "合成语料验收"},
        )
        assert dataset_response.status_code == 200, dataset_response.text
        dataset_id = dataset_response.json()["data"]["dataset_id"]

        upload_seconds: list[float] = []
        upload_failures = 0
        for document in corpus:
            started = perf_counter()
            response = client.post(
                f"/v1/datasets/{dataset_id}/documents",
                data={"project_id": str(project_id), "parse": "true"},
                files={
                    "file": (
                        document.filename,
                        document.content.encode("utf-8"),
                        "text/markdown",
                    )
                },
            )
            upload_seconds.append(perf_counter() - started)
            if response.status_code != 200:
                upload_failures += 1
                continue
            body = response.json()
            assert body["success"] is True
            assert body["data"]["filename"] == document.filename
            assert body["data"]["parse_started"] is True

        assert len(provider.parsed) == len(corpus)
        assert [upload["filename"] for upload in provider.uploads] == [
            document.filename for document in corpus
        ]

        recalled = 0
        locatable = 0
        paged_hits = 0
        for document in corpus:
            response = client.post(
                "/v1/retrieval",
                json={"project_id": str(project_id), "query": document.marker, "top_k": 5},
            )
            assert response.status_code == 200, response.text
            data = response.json()["data"]
            assert data["matched"] is True
            assert data["total"] == 1

            hit = data["hits"][0]
            if hit["title"] == document.filename and hit["source_path"] == document.source_path:
                recalled += 1
            if (
                hit["title"]
                and hit["source_path"] == document.source_path
                and tuple(hit["heading_path"]) == document.heading_path
                and document.marker in hit["snippet"]
            ):
                locatable += 1
            if document.page is not None:
                assert hit["page"] == document.page
                paged_hits += 1
            if document.category == "complex_table":
                assert "| 区域 | 折扣 | 最低采购量 |" in hit["snippet"]

        metrics = {
            "corpus": "synthetic",
            "documents": len(corpus),
            "scanned_pdf_documents": sum(document.category == "scanned_pdf" for document in corpus),
            "complex_table_documents": sum(
                document.category == "complex_table" for document in corpus
            ),
            "recall_hit_rate": recalled / len(corpus),
            "source_locatable_rate": locatable / len(corpus),
            "avg_synthetic_parse_seconds": sum(upload_seconds) / len(upload_seconds),
            "max_synthetic_parse_seconds": max(upload_seconds),
            "failure_rate": upload_failures / len(corpus),
            "paged_hits": paged_hits,
        }
        print(f"\nSYNTHETIC_CORPUS_METRICS={json.dumps(metrics, ensure_ascii=False)}")

    assert metrics["recall_hit_rate"] == 1.0
    assert metrics["source_locatable_rate"] == 1.0
    assert metrics["failure_rate"] == 0.0
    assert metrics["paged_hits"] == 3
    assert metrics["avg_synthetic_parse_seconds"] < 2.0
    assert metrics["max_synthetic_parse_seconds"] < 5.0
