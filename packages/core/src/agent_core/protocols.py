from __future__ import annotations

from datetime import datetime
from typing import Protocol, Self
from uuid import UUID

from .enums import CapabilityStatus, ReportKind
from .models import (
    Agent,
    AuditLog,
    CapabilityNote,
    Conversation,
    Document,
    Job,
    JobRun,
    KnowledgeBase,
    Message,
    Project,
    Report,
    ReportItem,
)
from .pagination import Page, PageRequest
from .values import CodeMatch, GitCommit, RetrievalHit, RetrievalQuery, TimeRange


class ProjectRepository(Protocol):
    def add(self, project: Project) -> Project: ...

    def update(self, project: Project) -> Project: ...

    def delete(self, project_id: UUID) -> None: ...

    def get(self, project_id: UUID) -> Project | None: ...

    def get_by_path(self, path: str) -> Project | None: ...

    def list(self, page: PageRequest, *, enabled: bool | None = None) -> Page[Project]: ...


class DocumentRepository(Protocol):
    def add(self, document: Document) -> Document: ...

    def update(self, document: Document) -> Document: ...

    def get(self, document_id: UUID) -> Document | None: ...

    def find_by_hash(self, project_id: UUID, content_hash: str) -> Document | None: ...

    def find_by_source_path(self, project_id: UUID, source_path: str) -> Document | None: ...

    def list_by_project(self, project_id: UUID, page: PageRequest) -> Page[Document]: ...


class KnowledgeBaseRepository(Protocol):
    def add(self, knowledge_base: KnowledgeBase) -> KnowledgeBase: ...

    def update(self, knowledge_base: KnowledgeBase) -> KnowledgeBase: ...

    def get_by_project(self, project_id: UUID) -> KnowledgeBase | None: ...


class ReportRepository(Protocol):
    def add(self, report: Report) -> Report: ...

    def update(self, report: Report) -> Report: ...

    def get(self, report_id: UUID) -> Report | None: ...

    def find_by_period(
        self, project_id: UUID, kind: ReportKind, start: datetime, end: datetime
    ) -> Report | None: ...

    def list_by_project(
        self,
        project_id: UUID,
        page: PageRequest,
        *,
        kind: ReportKind | None = None,
        period: TimeRange | None = None,
    ) -> Page[Report]: ...


class ReportItemRepository(Protocol):
    def add_many(self, items: tuple[ReportItem, ...]) -> tuple[ReportItem, ...]: ...

    def list_by_report(self, report_id: UUID) -> tuple[ReportItem, ...]: ...

    def delete_by_report(self, report_id: UUID) -> None: ...


class CapabilityNoteRepository(Protocol):
    def add(self, note: CapabilityNote) -> CapabilityNote: ...

    def update(self, note: CapabilityNote) -> CapabilityNote: ...

    def get(self, note_id: UUID) -> CapabilityNote | None: ...

    def find_by_topic(self, project_id: UUID, topic: str) -> CapabilityNote | None: ...

    def list_by_project(
        self,
        project_id: UUID,
        page: PageRequest,
        *,
        status: CapabilityStatus | None = None,
        topic: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> Page[CapabilityNote]: ...


class AgentRepository(Protocol):
    def get(self, agent_id: UUID) -> Agent | None: ...

    def list(self) -> tuple[Agent, ...]: ...


class JobRepository(Protocol):
    def get(self, job_id: UUID) -> Job | None: ...

    def list(self) -> tuple[Job, ...]: ...

    def list_enabled(self) -> tuple[Job, ...]: ...


class JobRunRepository(Protocol):
    def add(self, run: JobRun) -> JobRun: ...

    def update(self, run: JobRun) -> JobRun: ...

    def get(self, run_id: UUID) -> JobRun | None: ...

    def find_by_run_key(self, run_key: str) -> JobRun | None: ...

    def list_by_job(self, job_id: UUID, page: PageRequest) -> Page[JobRun]: ...

    def list_pending(self, limit: int = 100) -> tuple[JobRun, ...]: ...


class ConversationRepository(Protocol):
    def add(self, conversation: Conversation) -> Conversation: ...

    def update(self, conversation: Conversation) -> Conversation: ...

    def get(self, conversation_id: UUID) -> Conversation | None: ...

    def find_by_external_id(self, external_id: str) -> Conversation | None: ...

    def list_by_project(self, project_id: UUID, page: PageRequest) -> Page[Conversation]: ...


class MessageRepository(Protocol):
    def add(self, message: Message) -> Message: ...

    def list_by_conversation(self, conversation_id: UUID) -> tuple[Message, ...]: ...


class AuditLogRepository(Protocol):
    def add(self, log: AuditLog) -> AuditLog: ...

    def list(self, page: PageRequest, *, project_id: UUID | None = None) -> Page[AuditLog]: ...


class UnitOfWork(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool | None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class KnowledgeGateway(Protocol):
    def ensure_dataset(self, project: Project) -> KnowledgeBase: ...

    def upsert_document(self, project: Project, document: Document, content: str) -> str: ...

    def delete_document(self, project: Project, external_document_id: str) -> None: ...

    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievalHit, ...]: ...


class CodeAccess(Protocol):
    def read_file(
        self, project: Project, relative_path: str, *, max_bytes: int = 256_000
    ) -> str: ...

    def search(
        self, project: Project, query: str, *, max_results: int = 50
    ) -> tuple[CodeMatch, ...]: ...

    def git_log(
        self,
        project: Project,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> tuple[GitCommit, ...]: ...

    def git_diff(
        self, project: Project, *, base: str, head: str, max_bytes: int = 256_000
    ) -> str: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...
