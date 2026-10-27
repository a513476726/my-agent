from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from .repositories import (
    AgentRepository,
    AuditLogRepository,
    CapabilityNoteRepository,
    ConversationRepository,
    DocumentRepository,
    JobRepository,
    JobRunRepository,
    KnowledgeBaseRepository,
    MessageRepository,
    ProjectRepository,
    ReportItemRepository,
    ReportRepository,
)


class UnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> Self:
        session = self._session_factory()
        self.session = session
        self.projects = ProjectRepository(session)
        self.knowledge_bases = KnowledgeBaseRepository(session)
        self.documents = DocumentRepository(session)
        self.reports = ReportRepository(session)
        self.report_items = ReportItemRepository(session)
        self.capabilities = CapabilityNoteRepository(session)
        self.agents = AgentRepository(session)
        self.jobs = JobRepository(session)
        self.job_runs = JobRunRepository(session)
        self.conversations = ConversationRepository(session)
        self.messages = MessageRepository(session)
        self.audit_logs = AuditLogRepository(session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        session = self._require_session()
        try:
            if exc_type is None:
                session.commit()
            else:
                session.rollback()
        finally:
            session.close()
            self.session = None
        return None

    def commit(self) -> None:
        self._require_session().commit()

    def rollback(self) -> None:
        self._require_session().rollback()

    def _require_session(self) -> Session:
        if self.session is None:
            raise RuntimeError("UnitOfWork 必须在 with 语句中使用")
        return self.session
