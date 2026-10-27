from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from agent_core import MessageRole


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    agent_id: UUID | None
    title: str
    external_id: str | None
    created_at: datetime
    updated_at: datetime


class ToolCallResponse(BaseModel):
    name: str
    success: bool
    arguments: dict[str, object]
    error: str | None = None
    duration_ms: int | None = None


class CitationResponse(BaseModel):
    document_id: UUID
    document_title: str
    heading_path: list[str]
    snippet: str
    score: float | None = None
    page: int | None = None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    tool_calls: list[ToolCallResponse]
    citations: list[CitationResponse]
    created_at: datetime
    updated_at: datetime
