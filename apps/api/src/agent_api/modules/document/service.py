from __future__ import annotations

import hashlib
import posixpath
from pathlib import PurePosixPath
from uuid import uuid4

from agent_core import (
    AuditLog,
    ConflictError,
    Document,
    DocumentStatus,
    DomainValidationError,
    KnowledgeBase,
    Project,
    is_supported_document_filename,
    utc_now,
)
from agent_data import UnitOfWork

from ...knowledge import KnowledgeClient


def ingest_document(
    *,
    uow: UnitOfWork,
    knowledge: KnowledgeClient,
    project: Project,
    actor: str,
    filename: str,
    source_path: str | None,
    content: bytes,
    content_type: str | None,
) -> tuple[Document, bool]:
    normalized_filename = posixpath.basename(filename.replace("\\", "/")).strip()
    if not normalized_filename:
        raise DomainValidationError("文件名不能为空")
    if not content:
        raise DomainValidationError("文件内容不能为空")
    if not is_supported_document_filename(normalized_filename):
        raise DomainValidationError("不支持的文件格式")

    content_hash = hashlib.sha256(content).hexdigest()
    duplicate = uow.documents.find_by_hash(project.id, content_hash)
    if duplicate is not None:
        return duplicate, True

    normalized_source = (source_path or normalized_filename).replace("\\", "/").strip()
    normalized_source = posixpath.normpath(normalized_source).lstrip("/")
    if not normalized_source or normalized_source == ".":
        normalized_source = normalized_filename
    existing_path = uow.documents.find_by_source_path(project.id, normalized_source)
    if existing_path is not None:
        raise ConflictError("同名文档内容已变化，请使用增量同步更新")

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
        normalized_filename,
        content,
        content_type,
    )
    document = uow.documents.add(
        Document(
            id=uuid4(),
            project_id=project.id,
            knowledge_base_id=knowledge_base.id,
            title=PurePosixPath(normalized_filename).stem or normalized_filename,
            source_path=normalized_source,
            content_hash=content_hash,
            version=content_hash,
            external_document_id=uploaded.document_id,
            status=DocumentStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
    )
    uow.audit_logs.add(
        AuditLog(
            id=uuid4(),
            actor=actor,
            action="document.ingest",
            resource_type="document",
            resource_id=str(document.id),
            project_id=project.id,
            detail={
                "source_path": document.source_path,
                "content_hash": document.content_hash,
                "external_document_id": document.external_document_id,
            },
            created_at=now,
            updated_at=now,
        )
    )
    return document, False
