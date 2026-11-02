from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GrowBedCreate(BaseModel):
    system_id: UUID
    name: str = Field(min_length=1, max_length=100)
    crop_type: str | None = Field(default=None, max_length=100)
    capacity_description: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class GrowBedUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    crop_type: str | None = Field(default=None, max_length=100)
    capacity_description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class GrowBedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    name: str
    crop_type: str | None
    capacity_description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
