from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select

from agent_core import (
    CommitRange,
    Page,
    PageRequest,
    Report,
    ReportItem,
    ReportKind,
    ReportStatus,
    TimeRange,
)

from ..models.report import Report as ReportModel
from ..models.report import ReportItem as ReportItemModel
from .base import BaseRepository


def _report_to_domain(row: ReportModel) -> Report:
    return Report(
        id=row.id,
        project_id=row.project_id,
        job_run_id=row.job_run_id,
        kind=ReportKind(row.kind),
        period=TimeRange(start=row.period_start, end=row.period_end),
        title=row.title,
        body=row.body,
        status=ReportStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _report_item_to_domain(row: ReportItemModel) -> ReportItem:
    return ReportItem(
        id=row.id,
        report_id=row.report_id,
        project_id=row.project_id,
        title=row.title,
        summary=row.summary,
        category=row.category,
        commit_range=CommitRange(start_commit=row.commit_start, end_commit=row.commit_end),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ReportRepository(BaseRepository[ReportModel]):
    model = ReportModel

    def add(self, report: Report) -> Report:
        row = ReportModel(
            id=report.id,
            project_id=report.project_id,
            job_run_id=report.job_run_id,
            kind=report.kind.value,
            period_start=report.period.start,
            period_end=report.period.end,
            title=report.title,
            body=report.body,
            status=report.status.value,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )
        return _report_to_domain(self._add(row))

    def update(self, report: Report) -> Report:
        row = self._require(report.id)
        row.job_run_id = report.job_run_id
        row.kind = report.kind.value
        row.period_start = report.period.start
        row.period_end = report.period.end
        row.title = report.title
        row.body = report.body
        row.status = report.status.value
        self.session.flush()
        self.session.refresh(row)
        return _report_to_domain(row)

    def get(self, report_id: UUID) -> Report | None:
        row = self._get(report_id)
        return _report_to_domain(row) if row else None

    def find_by_period(
        self, project_id: UUID, kind: ReportKind, start: datetime, end: datetime
    ) -> Report | None:
        row = self.session.scalar(
            select(ReportModel).where(
                ReportModel.project_id == project_id,
                ReportModel.kind == kind.value,
                ReportModel.period_start == start,
                ReportModel.period_end == end,
            )
        )
        return _report_to_domain(row) if row else None

    def list_by_project(
        self,
        project_id: UUID,
        page: PageRequest,
        *,
        kind: ReportKind | None = None,
        period: TimeRange | None = None,
    ) -> Page[Report]:
        stmt = (
            select(ReportModel)
            .where(ReportModel.project_id == project_id)
            .order_by(ReportModel.period_start.desc(), ReportModel.id)
        )
        if kind is not None:
            stmt = stmt.where(ReportModel.kind == kind.value)
        if period is not None:
            stmt = stmt.where(
                ReportModel.period_start <= period.end,
                ReportModel.period_end >= period.start,
            )
        rows, total = self._paginate(stmt, page)
        return Page(records=tuple(_report_to_domain(row) for row in rows), total=total)


class ReportItemRepository(BaseRepository[ReportItemModel]):
    model = ReportItemModel

    def add_many(self, items: tuple[ReportItem, ...]) -> tuple[ReportItem, ...]:
        rows = [
            ReportItemModel(
                id=item.id,
                report_id=item.report_id,
                project_id=item.project_id,
                title=item.title,
                summary=item.summary,
                category=item.category,
                commit_start=item.commit_range.start_commit,
                commit_end=item.commit_range.end_commit,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ]
        for row in rows:
            self._add(row)
        return tuple(_report_item_to_domain(row) for row in rows)

    def list_by_report(self, report_id: UUID) -> tuple[ReportItem, ...]:
        rows = self.session.scalars(
            select(ReportItemModel)
            .where(ReportItemModel.report_id == report_id)
            .order_by(ReportItemModel.created_at, ReportItemModel.id)
        ).all()
        return tuple(_report_item_to_domain(row) for row in rows)

    def delete_by_report(self, report_id: UUID) -> None:
        self.session.execute(delete(ReportItemModel).where(ReportItemModel.report_id == report_id))
        self.session.flush()
