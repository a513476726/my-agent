from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from agent_core import JobKind, JobRunStatus, TriggerType

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Agent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default=JobKind.DAILY_GIT.value)
    cron: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class JobRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "job_runs"
    __table_args__ = (
        Index("ix_job_runs_job_created_at", "job_id", "created_at"),
        Index("ix_job_runs_project_status", "project_id", "status"),
    )

    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    run_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=JobRunStatus.PENDING.value
    )
    trigger: Mapped[str] = mapped_column(
        String(16), nullable=False, default=TriggerType.SCHEDULE.value
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )
