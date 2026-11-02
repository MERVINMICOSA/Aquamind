from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import SystemEventSeverity


class SystemEventCreate(BaseModel):
    system_id: UUID
    event_type: str = Field(
        min_length=1,
        max_length=64,
    )
    severity: SystemEventSeverity
    message: str = Field(
        min_length=1,
        max_length=1000,
    )
    event_metadata: dict | None = None
    occurred_at: datetime


class SystemEventUpdate(BaseModel):
    event_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    severity: SystemEventSeverity | None = None
    message: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
    )
    event_metadata: dict | None = None
    occurred_at: datetime | None = None


class SystemEventResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    system_id: UUID
    event_type: str
    severity: SystemEventSeverity
    message: str
    event_metadata: dict | None
    occurred_at: datetime