from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.enums import (
    ActuatorCommandType,
    ExecutionStatus,
    TriggerSource,
)


class ActuatorEventBase(BaseModel):
    actuator_id: UUID
    command_type: ActuatorCommandType
    requested_value: float | None = None
    actual_value: float | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    trigger_source: TriggerSource
    status: ExecutionStatus
    fault_code: str | None = None
    error_message: str | None = None


class ActuatorEventCreate(ActuatorEventBase):
    pass


class ActuatorEventUpdate(BaseModel):
    actual_value: float | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    status: ExecutionStatus | None = None
    fault_code: str | None = None
    error_message: str | None = None


class ActuatorEventResponse(ActuatorEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
