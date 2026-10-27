from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from agent_core import NotFoundError, PageRequest


class BaseRepository[ModelT]:
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def _get(self, entity_id: UUID) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def _require(self, entity_id: UUID) -> ModelT:
        row = self._get(entity_id)
        if row is None:
            raise NotFoundError(f"{self.model.__name__} 不存在: {entity_id}")
        return row

    def _paginate(self, stmt: Select, page: PageRequest) -> tuple[list[ModelT], int]:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = self.session.scalar(count_stmt) or 0
        rows = self.session.scalars(stmt.limit(page.limit).offset(page.offset)).all()
        return list(rows), total

    def _add(self, row: ModelT) -> ModelT:
        self.session.add(row)
        self.session.flush()
        self.session.refresh(row)
        return row

    def _delete(self, row: ModelT) -> None:
        self.session.delete(row)
        self.session.flush()
