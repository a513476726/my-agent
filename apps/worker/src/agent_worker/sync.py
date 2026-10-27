from __future__ import annotations

import argparse
import hashlib
import json
import logging
import mimetypes
import os
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from agent_core import (
    AuditLog,
    ConflictError,
    Document,
    DocumentStatus,
    DomainError,
    DomainValidationError,
    KnowledgeBase,
    NotFoundError,
    Project,
    is_supported_document_filename,
    utc_now,
)
from agent_data import UnitOfWork, build_engine, build_session_factory

from .knowledge import HttpKnowledgeClient, KnowledgeClient

logger = logging.getLogger(__name__)

_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".idea",
        ".next",
        ".venv",
        ".vscode",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
)


@dataclass(frozen=True, slots=True)
class SyncFailure:
    source_path: str
    message: str


@dataclass(frozen=True, slots=True)
class SyncResult:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    failed: tuple[SyncFailure, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "added": self.added,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": [
                {"source_path": failure.source_path, "message": failure.message}
                for failure in self.failed
            ],
        }


def _resolve_source_root(project: Project, source_dir: str) -> Path:
    project_root = Path(project.path).resolve()
    if not project_root.is_dir():
        raise DomainValidationError(f"项目目录不存在: {project.path}")

    relative = PurePosixPath(source_dir.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise DomainValidationError("source_dir 必须位于项目目录内")
    source_root = (project_root / Path(*relative.parts)).resolve()
    if not source_root.is_relative_to(project_root) or not source_root.is_dir():
        raise DomainValidationError(f"同步目录不存在或越界: {source_dir}")
    return source_root


def _iter_document_paths(source_root: Path, project_root: Path) -> Iterator[Path]:
    for path in sorted(source_root.rglob("*")):
        relative_parts = path.relative_to(source_root).parts
        if any(part in _EXCLUDED_DIRECTORIES for part in relative_parts[:-1]):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if not is_supported_document_filename(path.name):
            continue
        if not path.resolve().is_relative_to(project_root):
            continue
        yield path


def _ensure_knowledge_base(
    session_factory: sessionmaker[Session],
    knowledge: KnowledgeClient,
    project: Project,
) -> KnowledgeBase:
    with UnitOfWork(session_factory) as uow:
        existing = uow.knowledge_bases.get_by_project(project.id)
        if existing is not None:
            return existing
        dataset = knowledge.ensure_dataset(project.id, project.name)
        now = utc_now()
        return uow.knowledge_bases.add(
            KnowledgeBase(
                id=uuid4(),
                project_id=project.id,
                name=dataset.name,
                dataset_id=dataset.dataset_id,
                created_at=now,
                updated_at=now,
            )
        )


def _sync_file(
    *,
    session_factory: sessionmaker[Session],
    knowledge: KnowledgeClient,
    project: Project,
    knowledge_base: KnowledgeBase,
    path: Path,
    project_root: Path,
    actor: str,
) -> str:
    content = path.read_bytes()
    if not content:
        raise DomainValidationError("文件内容不能为空")

    source_path = path.relative_to(project_root).as_posix()
    content_hash = hashlib.sha256(content).hexdigest()
    content_type = mimetypes.guess_type(path.name)[0]
    new_external_id: str | None = None
    old_external_id: str | None = None
    outcome = "skipped"

    try:
        with UnitOfWork(session_factory) as uow:
            existing_path = uow.documents.find_by_source_path(project.id, source_path)
            if existing_path is not None and existing_path.content_hash == content_hash:
                return "skipped"

            existing_hash = uow.documents.find_by_hash(project.id, content_hash)
            if existing_hash is not None and (
                existing_path is None or existing_hash.id != existing_path.id
            ):
                return "skipped"

            uploaded = knowledge.upload_document(
                project.id,
                knowledge_base.dataset_id,
                path.name,
                content,
                content_type,
            )
            new_external_id = uploaded.document_id
            now = utc_now()
            title = path.stem or path.name

            if existing_path is None:
                document = Document(
                    id=uuid4(),
                    project_id=project.id,
                    knowledge_base_id=knowledge_base.id,
                    title=title,
                    source_path=source_path,
                    content_hash=content_hash,
                    version=content_hash,
                    external_document_id=new_external_id,
                    status=DocumentStatus.PENDING,
                    created_at=now,
                    updated_at=now,
                )
                uow.documents.add(document)
                action = "document.sync.create"
                outcome = "added"
            else:
                old_external_id = existing_path.external_document_id
                document = replace(
                    existing_path,
                    title=title,
                    content_hash=content_hash,
                    version=content_hash,
                    external_document_id=new_external_id,
                    status=DocumentStatus.PENDING,
                    updated_at=now,
                )
                uow.documents.update(document)
                action = "document.sync.update"
                outcome = "updated"

            uow.audit_logs.add(
                AuditLog(
                    id=uuid4(),
                    actor=actor,
                    action=action,
                    resource_type="document",
                    resource_id=str(document.id),
                    project_id=project.id,
                    detail={
                        "source_path": source_path,
                        "content_hash": content_hash,
                        "external_document_id": new_external_id,
                        "previous_content_hash": existing_path.content_hash
                        if existing_path is not None
                        else None,
                    },
                    created_at=now,
                    updated_at=now,
                )
            )
    except Exception:
        if new_external_id is not None:
            try:
                knowledge.delete_document(project.id, knowledge_base.dataset_id, new_external_id)
            except Exception:
                logger.exception("同步失败后清理新文档失败: %s", source_path)
        raise

    if old_external_id is not None:
        try:
            knowledge.delete_document(project.id, knowledge_base.dataset_id, old_external_id)
        except Exception:
            logger.exception("旧版本文档删除失败，需后续对账: %s", source_path)
    return outcome


def sync_project(
    session_factory: sessionmaker[Session],
    knowledge: KnowledgeClient,
    project: Project,
    *,
    actor: str,
    source_dir: str = ".",
) -> SyncResult:
    if not project.enabled:
        raise ConflictError("项目已停用")
    if not actor.strip():
        raise DomainValidationError("actor 不能为空")

    project_root = Path(project.path).resolve()
    source_root = _resolve_source_root(project, source_dir)
    knowledge_base = _ensure_knowledge_base(session_factory, knowledge, project)
    added = updated = skipped = 0
    failures: list[SyncFailure] = []

    for path in _iter_document_paths(source_root, project_root):
        source_path = path.relative_to(project_root).as_posix()
        try:
            outcome = _sync_file(
                session_factory=session_factory,
                knowledge=knowledge,
                project=project,
                knowledge_base=knowledge_base,
                path=path,
                project_root=project_root,
                actor=actor,
            )
        except Exception as exc:
            logger.exception("文档同步失败: %s", source_path)
            failures.append(SyncFailure(source_path=source_path, message=str(exc)))
            continue
        if outcome == "added":
            added += 1
        elif outcome == "updated":
            updated += 1
        else:
            skipped += 1

    return SyncResult(
        added=added,
        updated=updated,
        skipped=skipped,
        failed=tuple(failures),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="按项目增量同步文档到知识库")
    parser.add_argument("--project-id", required=True, type=UUID, help="项目 UUID")
    parser.add_argument("--source-dir", default=".", help="项目内的相对同步目录，默认整个项目")
    parser.add_argument("--actor", default="system:sync", help="审计日志操作者")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="数据库连接串")
    parser.add_argument(
        "--knowledge-base-url",
        default=os.getenv("KNOWLEDGE_BASE_URL", "http://127.0.0.1:8010"),
        help="知识库网关地址",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("KNOWLEDGE_TIMEOUT_SECONDS", "30")),
        help="知识库请求超时秒数",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.database_url:
        parser.error("必须提供 --database-url 或 DATABASE_URL")

    engine = build_engine(args.database_url)
    try:
        session_factory = build_session_factory(engine)
        with UnitOfWork(session_factory) as uow:
            project = uow.projects.get(args.project_id)
        if project is None:
            raise NotFoundError("项目不存在")
        with HttpKnowledgeClient(
            base_url=args.knowledge_base_url,
            timeout_seconds=args.timeout,
        ) as knowledge:
            result = sync_project(
                session_factory,
                knowledge,
                project,
                actor=args.actor,
                source_dir=args.source_dir,
            )
    except DomainError as exc:
        print(json.dumps({"error": exc.message}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        engine.dispose()

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
