from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MenuMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str


class MenuItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    path: str
    label: str | None = None
    meta: MenuMeta | None = None
    children: list[MenuItem] = Field(default_factory=list)


class UserInfoResponse(BaseModel):
    username: str
    nickname: str | None = None
    avatar: str | None = None
    roles: list[str]


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor: str
    action: str
    resource_type: str
    resource_id: str | None = None
    project_id: UUID | None = None
    detail: dict[str, object] | None = None
    created_at: datetime
    updated_at: datetime


MenuItem.model_rebuild()
