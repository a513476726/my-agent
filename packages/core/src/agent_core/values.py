from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .errors import DomainValidationError
from .validation import ensure_aware, require_non_negative, require_positive, require_text


@dataclass(frozen=True, slots=True, kw_only=True)
class TimeRange:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        ensure_aware(self.start, "start")
        ensure_aware(self.end, "end")
        if self.end <= self.start:
            raise DomainValidationError("end 必须晚于 start")


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitRange:
    start_commit: str
    end_commit: str

    def __post_init__(self) -> None:
        require_text(self.start_commit, "start_commit")
        require_text(self.end_commit, "end_commit")


@dataclass(frozen=True, slots=True, kw_only=True)
class Citation:
    document_id: UUID
    document_title: str
    heading_path: tuple[str, ...]
    snippet: str
    score: float | None = None
    page: int | None = None

    def __post_init__(self) -> None:
        require_text(self.document_title, "document_title")
        require_text(self.snippet, "snippet")
        for heading in self.heading_path:
            require_text(heading, "heading_path")
        if self.score is not None:
            require_non_negative(self.score, "score")
        if self.page is not None:
            require_positive(self.page, "page")


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolCallSummary:
    name: str
    success: bool
    arguments: tuple[tuple[str, object], ...] = ()
    error: str | None = None
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        require_text(self.name, "name")
        for key, _ in self.arguments:
            require_text(key, "arguments key")
        if not self.success and not (self.error and self.error.strip()):
            raise DomainValidationError("失败的工具调用必须记录 error")
        if self.duration_ms is not None:
            require_non_negative(self.duration_ms, "duration_ms")


@dataclass(frozen=True, slots=True, kw_only=True)
class RetrievalQuery:
    project_id: UUID
    text: str
    top_k: int = 5

    def __post_init__(self) -> None:
        require_text(self.text, "text")
        if not 1 <= self.top_k <= 50:
            raise DomainValidationError("top_k 必须在 1 到 50 之间")


@dataclass(frozen=True, slots=True, kw_only=True)
class RetrievalHit:
    document_id: UUID
    title: str
    source_path: str
    heading_path: tuple[str, ...]
    snippet: str
    score: float
    page: int | None = None

    def __post_init__(self) -> None:
        require_text(self.title, "title")
        require_text(self.source_path, "source_path")
        require_text(self.snippet, "snippet")
        for heading in self.heading_path:
            require_text(heading, "heading_path")
        require_non_negative(self.score, "score")
        if self.page is not None:
            require_positive(self.page, "page")


@dataclass(frozen=True, slots=True, kw_only=True)
class CodeMatch:
    path: str
    line: int
    snippet: str

    def __post_init__(self) -> None:
        require_text(self.path, "path")
        require_positive(self.line, "line")
        require_text(self.snippet, "snippet")


@dataclass(frozen=True, slots=True, kw_only=True)
class GitCommit:
    sha: str
    author: str
    committed_at: datetime
    message: str

    def __post_init__(self) -> None:
        require_text(self.sha, "sha")
        require_text(self.author, "author")
        ensure_aware(self.committed_at, "committed_at")
        require_text(self.message, "message")
