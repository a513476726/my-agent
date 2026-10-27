from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from agent_core import CapabilityNote, CapabilityStatus, Page, PageRequest

from ..models.capability import CapabilityNote as CapabilityNoteModel
from .base import BaseRepository


def _capability_to_domain(row: CapabilityNoteModel) -> CapabilityNote:
    return CapabilityNote(
        id=row.id,
        project_id=row.project_id,
        source_report_ids=tuple(UUID(item) for item in row.source_report_ids),
        topic=row.topic,
        content=row.content,
        tags=tuple(row.tags),
        status=CapabilityStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class CapabilityNoteRepository(BaseRepository[CapabilityNoteModel]):
    model = CapabilityNoteModel

    def add(self, note: CapabilityNote) -> CapabilityNote:
        row = CapabilityNoteModel(
            id=note.id,
            project_id=note.project_id,
            source_report_ids=[str(item) for item in note.source_report_ids],
            topic=note.topic,
            content=note.content,
            tags=list(note.tags),
            status=note.status.value,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        return _capability_to_domain(self._add(row))

    def update(self, note: CapabilityNote) -> CapabilityNote:
        row = self._require(note.id)
        row.source_report_ids = [str(item) for item in note.source_report_ids]
        row.topic = note.topic
        row.content = note.content
        row.tags = list(note.tags)
        row.status = note.status.value
        self.session.flush()
        self.session.refresh(row)
        return _capability_to_domain(row)

    def get(self, note_id: UUID) -> CapabilityNote | None:
        row = self._get(note_id)
        return _capability_to_domain(row) if row else None

    def find_by_topic(self, project_id: UUID, topic: str) -> CapabilityNote | None:
        row = self.session.scalar(
            select(CapabilityNoteModel).where(
                CapabilityNoteModel.project_id == project_id,
                CapabilityNoteModel.topic == topic,
            )
        )
        return _capability_to_domain(row) if row else None

    def list_by_project(
        self,
        project_id: UUID,
        page: PageRequest,
        *,
        status: CapabilityStatus | None = None,
        topic: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> Page[CapabilityNote]:
        stmt = (
            select(CapabilityNoteModel)
            .where(CapabilityNoteModel.project_id == project_id)
            .order_by(CapabilityNoteModel.updated_at.desc(), CapabilityNoteModel.id)
        )
        if status is not None:
            stmt = stmt.where(CapabilityNoteModel.status == status.value)
        if topic is not None:
            stmt = stmt.where(CapabilityNoteModel.topic == topic)
        for tag in tags:
            stmt = stmt.where(CapabilityNoteModel.tags.contains([tag]))
        rows, total = self._paginate(stmt, page)
        return Page(records=tuple(_capability_to_domain(row) for row in rows), total=total)
