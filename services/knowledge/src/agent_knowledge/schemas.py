from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DatasetCreateRequest(BaseModel):
    project_id: UUID
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name 不能为空")
        return stripped


class DatasetResponse(BaseModel):
    project_id: UUID
    dataset_id: str
    name: str


class DocumentUploadResponse(BaseModel):
    dataset_id: str
    document_id: str
    filename: str
    parse_started: bool


class RetrievalRequest(BaseModel):
    project_id: UUID
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query 不能为空")
        return stripped


class RetrievalHitResponse(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source_path: str
    heading_path: list[str]
    snippet: str
    score: float
    page: int | None = None


class RetrievalResponse(BaseModel):
    hits: list[RetrievalHitResponse]
    total: int
    matched: bool
