from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from agent_core import (
    CapabilityNote,
    PageRequest,
    Project,
    Report,
    ReportItem,
    ReportStatus,
    TimeRange,
    utc_now,
)
from agent_data import UnitOfWork

_CONVENTIONAL_PREFIX = re.compile(r"^[a-zA-Z]+(?:\([^)]*\))?!?:\s*")
_MAX_TOPIC_LENGTH = 500


@dataclass(frozen=True, slots=True)
class SedimentResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    notes: tuple[CapabilityNote, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "notes": [str(note.id) for note in self.notes],
        }


def sediment_capabilities(
    session_factory: sessionmaker[Session],
    project: Project,
    *,
    at: datetime | None = None,
    lookback_days: int = 8,
    report_ids: tuple[UUID, ...] = (),
) -> SedimentResult:
    if lookback_days < 1:
        raise ValueError("lookback_days 必须大于 0")
    now = at or utc_now()
    created = 0
    updated = 0
    skipped = 0
    touched: list[CapabilityNote] = []

    with UnitOfWork(session_factory) as uow:
        reports = _load_reports(
            uow,
            project.id,
            start=now - timedelta(days=lookback_days),
            end=now,
            report_ids=report_ids,
        )
        for report in reports:
            if report.status is not ReportStatus.READY:
                continue
            items = uow.report_items.list_by_report(report.id)
            for item in items:
                if item.project_id != project.id:
                    continue
                topic = _topic_for(item)
                content = _content_for(item)
                existing = uow.capabilities.find_by_topic(project.id, topic)
                if existing is None:
                    created += 1
                    note = uow.capabilities.add(
                        CapabilityNote(
                            id=uuid4(),
                            project_id=project.id,
                            source_report_ids=(report.id,),
                            topic=topic,
                            content=content,
                            tags=(item.category,),
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    touched.append(note)
                    continue

                sources = _append_sources(existing.source_report_ids, (report.id,))
                tags = _append_sources(existing.tags, (item.category,))
                merged_content = _merge_content(existing.content, content)
                if (
                    sources == existing.source_report_ids
                    and tags == existing.tags
                    and merged_content == existing.content
                ):
                    skipped += 1
                    touched.append(existing)
                    continue
                updated += 1
                note = uow.capabilities.update(
                    replace(
                        existing,
                        source_report_ids=sources,
                        content=merged_content,
                        tags=tags,
                        updated_at=now,
                    )
                )
                touched.append(note)

    return SedimentResult(
        created=created,
        updated=updated,
        skipped=skipped,
        notes=tuple(touched),
    )


def _load_reports(
    uow: UnitOfWork,
    project_id: UUID,
    *,
    start: datetime,
    end: datetime,
    report_ids: tuple[UUID, ...],
) -> tuple[Report, ...]:
    if report_ids:
        reports = (uow.reports.get(report_id) for report_id in report_ids)
        return tuple(
            report for report in reports if report is not None and report.project_id == project_id
        )

    records: list[Report] = []
    offset = 0
    while True:
        page = uow.reports.list_by_project(
            project_id,
            PageRequest(limit=200, offset=offset),
            period=TimeRange(start=start, end=end),
        )
        records.extend(page.records)
        offset += len(page.records)
        if offset >= page.total or not page.records:
            break
    return tuple(records)


def _topic_for(item: ReportItem) -> str:
    topic = _CONVENTIONAL_PREFIX.sub("", item.title).strip()
    topic = " ".join(topic.split())
    return (topic or item.title.strip())[:_MAX_TOPIC_LENGTH]


def _content_for(item: ReportItem) -> str:
    return f"{item.title.strip()}\n\n{item.summary.strip()}"


def _append_sources[T](existing: tuple[T, ...], incoming: tuple[T, ...]) -> tuple[T, ...]:
    merged = list(existing)
    for value in incoming:
        if value not in merged:
            merged.append(value)
    return tuple(merged)


def _merge_content(existing: str, incoming: str) -> str:
    if incoming in existing:
        return existing
    return f"{existing.rstrip()}\n\n{incoming.strip()}"
