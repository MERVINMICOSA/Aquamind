from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import ActuatorState, ActuatorType, ControlMode, LocationType


class ActuatorBase(BaseModel):
    system_id: UUID
    name: str = Field(min_length=1, max_length=100)
    actuator_type: ActuatorType
    control_mode: ControlMode
    hardware_identifier: str | None = Field(default=None, max_length=150)
    location_type: LocationType | None = None
    location_id: UUID | None = None
    is_enabled: bool = True
    safety_config: dict | None = None
    current_state: ActuatorState = ActuatorState.OFF
    current_value: float | None = None
    last_state_at: datetime | None = None


class ActuatorCreate(ActuatorBase):
    pass


class ActuatorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    actuator_type: ActuatorType | None = None
    control_mode: ControlMode | None = None
    hardware_identifier: str | None = Field(default=None, max_length=150)
    location_type: LocationType | None = None
    location_id: UUID | None = None
    is_enabled: bool | None = None
    safety_config: dict | None = None
    current_state: ActuatorState | None = None
    current_value: float | None = None
    last_state_at: datetime | None = None


class ActuatorResponse(ActuatorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None