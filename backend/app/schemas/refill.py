from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.enums import ExecutionStatus, RefillTrigger


class RefillEventCreate(BaseModel):
    reservoir_id: UUID
    target_tank_id: UUID
    start_level_percent: float
    end_level_percent: float
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    trigger: RefillTrigger
    status: ExecutionStatus
    timeout_reason: str | None = None


class RefillEventUpdate(BaseModel):
    reservoir_id: UUID | None = None
    target_tank_id: UUID | None = None
    start_level_percent: float | None = None
    end_level_percent: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    trigger: RefillTrigger | None = None
    status: ExecutionStatus | None = None
    timeout_reason: str | None = None


class RefillEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reservoir_id: UUID
    target_tank_id: UUID
    start_level_percent: float
    end_level_percent: float
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None
    trigger: RefillTrigger
    status: ExecutionStatus
    timeout_reason: str | None
    created_at: datetime
