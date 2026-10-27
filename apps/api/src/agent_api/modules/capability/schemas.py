from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from agent_core import CapabilityStatus, DocumentStatus


class CapabilityNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    source_report_ids: list[UUID]
    topic: str
    content: str
    tags: list[str]
    status: CapabilityStatus
    created_at: datetime
    updated_at: datetime


class CapabilityStatusUpdate(BaseModel):
    project_id: UUID
    status: CapabilityStatus


class CapabilitySyncRequest(BaseModel):
    project_id: UUID


class CapabilitySyncDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    knowledge_base_id: UUID | None
    title: str
    source_path: str
    content_hash: str
    external_document_id: str | None
    status: DocumentStatus


class CapabilitySyncResponse(BaseModel):
    note: CapabilityNoteResponse
    document: CapabilitySyncDocumentResponse
    deduplicated: bool
