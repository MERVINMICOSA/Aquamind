from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SystemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    timezone: str = Field(default="UTC", max_length=64)
    is_active: bool = True


class SystemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    timezone: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


class SystemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime