from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from agent_core import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    knowledge_base_id: UUID | None
    title: str
    source_path: str
    content_hash: str
    version: str
    external_document_id: str | None = None
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


class DocumentIngestResponse(DocumentResponse):
    deduplicated: bool
