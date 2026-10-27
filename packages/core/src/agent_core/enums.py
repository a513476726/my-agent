from __future__ import annotations

from enum import StrEnum


class VcsType(StrEnum):
    GIT = "git"
    SVN = "svn"
    NONE = "none"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class ReportKind(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    QUARTERLY = "quarterly"


class ReportStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    FAILED = "failed"


class CapabilityStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    ARCHIVED = "archived"


class JobKind(StrEnum):
    DAILY_GIT = "daily_git"
    WEEKLY_GIT = "weekly_git"
    QUARTERLY_GIT = "quarterly_git"
    CAPABILITY_SEDIMENT = "capability_sediment"
    KNOWLEDGE_SYNC = "knowledge_sync"


class JobRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class TriggerType(StrEnum):
    SCHEDULE = "schedule"
    MANUAL = "manual"


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
