from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReservoirCreate(BaseModel):
    system_id: UUID
    name: str = Field(min_length=1, max_length=100)
    capacity_liters: float = Field(gt=0)
    is_active: bool = True


class ReservoirUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    capacity_liters: float | None = Field(default=None, gt=0)
    is_active: bool | None = None


class ReservoirResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    name: str
    capacity_liters: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
