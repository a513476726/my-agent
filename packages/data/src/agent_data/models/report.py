from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_core import ReportKind, ReportStatus

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Report(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "kind",
            "period_start",
            "period_end",
            name="uq_reports_project_kind_period",
        ),
        Index("ix_reports_project_created_at", "project_id", "created_at"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    job_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "job_runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_reports_job_run_id_job_runs",
        ),
        nullable=True,
        unique=True,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default=ReportKind.DAILY.value)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ReportStatus.READY.value
    )


class ReportItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "report_items"
    __table_args__ = (Index("ix_report_items_report_id", "report_id"),)

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    commit_start: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_end: Mapped[str] = mapped_column(String(64), nullable=False)
