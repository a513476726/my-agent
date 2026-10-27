from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agent_core import VcsType


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    path: str = Field(min_length=1, max_length=2000)
    vcs_type: VcsType = VcsType.GIT
    enabled: bool = True


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    path: str
    vcs_type: VcsType
    enabled: bool
    created_at: datetime
    updated_at: datetime
