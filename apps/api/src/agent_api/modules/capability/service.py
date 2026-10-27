from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import uuid4

from agent_core import (
    AuditLog,
    CapabilityNote,
    CapabilityStatus,
    ConflictError,
    Document,
    DocumentStatus,
    KnowledgeBase,
    Project,
    utc_now,
)
from agent_data import UnitOfWork

from ...knowledge import KnowledgeClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CapabilitySyncResult:
    document: Document
    deduplicated: bool


def update_capability_status(
    uow: UnitOfWork,
    *,
    note: CapabilityNote,
    status: CapabilityStatus,
    actor: str,
    at: datetime | None = None,
) -> CapabilityNote:
    now = at or utc_now()
    updated = uow.capabilities.update(replace(note, status=status, updated_at=now))
    uow.audit_logs.add(
        AuditLog(
            id=uuid4(),
            actor=actor,
            action="capability.status.update",
            resource_type="capability_note",
            resource_id=str(updated.id),
            project_id=updated.project_id,
            detail={"from": note.status.value, "to": status.value},
            created_at=now,
            updated_at=now,
        )
    )
    return updated


def sync_capability_to_knowledge(
    uow: UnitOfWork,
    knowledge: KnowledgeClient,
    *,
    project: Project,
    note: CapabilityNote,
    actor: str,
) -> CapabilitySyncResult:
    if note.status is not CapabilityStatus.CONFIRMED:
        raise ConflictError("只有已确认的能力条目可以同步到知识库")
    if not project.enabled:
        raise ConflictError("项目已停用")

    content = _render_markdown(note).encode("utf-8")
    content_hash = hashlib.sha256(content).hexdigest()
    source_path = f"capabilities/{note.id}.md"
    existing = uow.documents.find_by_source_path(project.id, source_path)
    if (
        existing is not None
        and existing.content_hash == content_hash
        and existing.external_document_id
    ):
        return CapabilitySyncResult(document=existing, deduplicated=True)

    now = utc_now()
    knowledge_base = uow.knowledge_bases.get_by_project(project.id)
    if knowledge_base is None:
        dataset = knowledge.ensure_dataset(project.id, project.name)
        knowledge_base = uow.knowledge_bases.add(
            KnowledgeBase(
                id=uuid4(),
                project_id=project.id,
                name=dataset.name,
                dataset_id=dataset.dataset_id,
                created_at=now,
                updated_at=now,
            )
        )

    uploaded = knowledge.upload_document(
        project.id,
        knowledge_base.dataset_id,
        f"capability-{note.id}.md",
        content,
        "text/markdown",
    )
    old_external_id = existing.external_document_id if existing is not None else None
    try:
        if existing is None:
            document = uow.documents.add(
                Document(
                    id=uuid4(),
                    project_id=project.id,
                    knowledge_base_id=knowledge_base.id,
                    title=note.topic,
                    source_path=source_path,
                    content_hash=content_hash,
                    version=content_hash,
                    external_document_id=uploaded.document_id,
                    status=DocumentStatus.PENDING,
                    created_at=now,
                    updated_at=now,
                )
            )
            action = "capability.knowledge_sync.created"
        else:
            document = uow.documents.update(
                replace(
                    existing,
                    knowledge_base_id=knowledge_base.id,
                    title=note.topic,
                    content_hash=content_hash,
                    version=content_hash,
                    external_document_id=uploaded.document_id,
                    status=DocumentStatus.PENDING,
                    updated_at=now,
                )
            )
            action = "capability.knowledge_sync.updated"

        uow.audit_logs.add(
            AuditLog(
                id=uuid4(),
                actor=actor,
                action=action,
                resource_type="capability_note",
                resource_id=str(note.id),
                project_id=project.id,
                detail={
                    "document_id": str(document.id),
                    "source_path": source_path,
                    "external_document_id": uploaded.document_id,
                    "content_hash": content_hash,
                },
                created_at=now,
                updated_at=now,
            )
        )
        uow.commit()
    except Exception:
        try:
            knowledge.delete_document(project.id, knowledge_base.dataset_id, uploaded.document_id)
        except Exception:
            logger.exception("能力条目同步失败后清理知识库文档失败: %s", note.id)
        raise

    if old_external_id is not None and old_external_id != uploaded.document_id:
        try:
            knowledge.delete_document(project.id, knowledge_base.dataset_id, old_external_id)
        except Exception:
            logger.exception("能力条目旧知识库文档删除失败，需后续对账: %s", note.id)
    return CapabilitySyncResult(document=document, deduplicated=False)


def _render_markdown(note: CapabilityNote) -> str:
    source_lines = "\n".join(f"- {report_id}" for report_id in note.source_report_ids)
    tag_line = "、".join(note.tags) if note.tags else "无"
    return (
        f"# {note.topic}\n\n"
        f"状态：已确认\n\n"
        f"标签：{tag_line}\n\n"
        "## 能力内容\n\n"
        f"{note.content.strip()}\n\n"
        "## 来源报告\n\n"
        f"{source_lines}\n"
    )
