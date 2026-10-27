from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from agent_core import MessageRole

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_project_updated_at", "project_id", "updated_at"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True)


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created_at", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=MessageRole.USER.value)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    citations: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created_at", "created_at"),)

    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    detail: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
