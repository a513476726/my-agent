from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .enums import (
    CapabilityStatus,
    DocumentStatus,
    JobKind,
    JobRunStatus,
    MessageRole,
    ReportKind,
    ReportStatus,
    TriggerType,
    VcsType,
)
from .errors import DomainValidationError
from .validation import ensure_aware, require_absolute_path, require_text
from .values import Citation, CommitRange, TimeRange, ToolCallSummary


@dataclass(frozen=True, slots=True, kw_only=True)
class Entity:
    id: UUID
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        ensure_aware(self.created_at, "created_at")
        ensure_aware(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise DomainValidationError("updated_at 不能早于 created_at")


@dataclass(frozen=True, slots=True, kw_only=True)
class Project(Entity):
    name: str
    path: str
    vcs_type: VcsType
    enabled: bool = True

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.name, "name")
        require_absolute_path(self.path, "path")


@dataclass(frozen=True, slots=True, kw_only=True)
class KnowledgeBase(Entity):
    project_id: UUID
    name: str
    dataset_id: str

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.name, "name")
        require_text(self.dataset_id, "dataset_id")


@dataclass(frozen=True, slots=True, kw_only=True)
class Document(Entity):
    project_id: UUID
    knowledge_base_id: UUID | None
    title: str
    source_path: str
    content_hash: str
    version: str
    external_document_id: str | None = None
    status: DocumentStatus = DocumentStatus.PENDING

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.title, "title")
        require_text(self.source_path, "source_path")
        require_text(self.content_hash, "content_hash")
        require_text(self.version, "version")
        if self.external_document_id is not None:
            require_text(self.external_document_id, "external_document_id")


@dataclass(frozen=True, slots=True, kw_only=True)
class Report(Entity):
    project_id: UUID
    job_run_id: UUID | None
    kind: ReportKind
    period: TimeRange
    title: str
    body: str
    status: ReportStatus = ReportStatus.READY

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.title, "title")
        require_text(self.body, "body")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportItem(Entity):
    report_id: UUID
    project_id: UUID
    title: str
    summary: str
    category: str
    commit_range: CommitRange

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.title, "title")
        require_text(self.summary, "summary")
        require_text(self.category, "category")


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityNote(Entity):
    project_id: UUID
    source_report_ids: tuple[UUID, ...]
    topic: str
    content: str
    tags: tuple[str, ...] = ()
    status: CapabilityStatus = CapabilityStatus.DRAFT

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        if not self.source_report_ids:
            raise DomainValidationError("source_report_ids 不能为空")
        require_text(self.topic, "topic")
        require_text(self.content, "content")
        for tag in self.tags:
            require_text(tag, "tags")


@dataclass(frozen=True, slots=True, kw_only=True)
class Agent(Entity):
    name: str
    model: str
    system_prompt: str
    enabled: bool = True

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.name, "name")
        require_text(self.model, "model")
        require_text(self.system_prompt, "system_prompt")


@dataclass(frozen=True, slots=True, kw_only=True)
class Job(Entity):
    name: str
    kind: JobKind
    cron: str
    enabled: bool = True
    config: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.name, "name")
        require_text(self.cron, "cron")
        for key, _ in self.config:
            require_text(key, "config key")


@dataclass(frozen=True, slots=True, kw_only=True)
class JobRun(Entity):
    job_id: UUID
    project_id: UUID
    run_key: str
    status: JobRunStatus = JobRunStatus.PENDING
    trigger: TriggerType = TriggerType.SCHEDULE
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    report_id: UUID | None = None

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.run_key, "run_key")
        if self.started_at is not None:
            ensure_aware(self.started_at, "started_at")
        if self.finished_at is not None:
            ensure_aware(self.finished_at, "finished_at")
        if self.started_at and self.finished_at and self.finished_at < self.started_at:
            raise DomainValidationError("finished_at 不能早于 started_at")
        if self.status == JobRunStatus.FAILED and not (
            self.error_message and self.error_message.strip()
        ):
            raise DomainValidationError("失败的运行必须记录 error_message")


@dataclass(frozen=True, slots=True, kw_only=True)
class Conversation(Entity):
    project_id: UUID
    agent_id: UUID | None
    title: str
    external_id: str | None = None

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.title, "title")


@dataclass(frozen=True, slots=True, kw_only=True)
class Message(Entity):
    conversation_id: UUID
    role: MessageRole
    content: str
    tool_calls: tuple[ToolCallSummary, ...] = ()
    citations: tuple[Citation, ...] = ()

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        if not self.content.strip() and not self.tool_calls:
            raise DomainValidationError("content 与 tool_calls 不能同时为空")


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditLog(Entity):
    actor: str
    action: str
    resource_type: str
    resource_id: str | None = None
    project_id: UUID | None = None
    detail: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_text(self.actor, "actor")
        require_text(self.action, "action")
        require_text(self.resource_type, "resource_type")
