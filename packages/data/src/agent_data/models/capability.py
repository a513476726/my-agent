from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from agent_core import CapabilityStatus

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CapabilityNote(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "capability_notes"
    __table_args__ = (
        UniqueConstraint("project_id", "topic", name="uq_capability_notes_project_topic"),
        Index("ix_capability_notes_project_status", "project_id", "status"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    source_report_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CapabilityStatus.DRAFT.value
    )
