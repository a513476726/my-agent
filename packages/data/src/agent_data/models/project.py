from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_core import DocumentStatus, VcsType

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    vcs_type: Mapped[str] = mapped_column(String(16), nullable=False, default=VcsType.GIT.value)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class KnowledgeBase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "knowledge_bases"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("project_id", "content_hash", name="uq_documents_project_content_hash"),
        UniqueConstraint("project_id", "source_path", name="uq_documents_project_source_path"),
        Index("ix_documents_project_status", "project_id", "status"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    knowledge_base_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    external_document_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True, unique=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DocumentStatus.PENDING.value
    )
