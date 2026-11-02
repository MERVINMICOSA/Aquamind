from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import AlertSeverity, AlertStatus


class AlertCreate(BaseModel):
    system_id: UUID
    sensor_id: UUID | None = None
    actuator_id: UUID | None = None
    alert_type: str = Field(min_length=1, max_length=64)
    severity: AlertSeverity
    message: str = Field(min_length=1, max_length=1000)
    trigger_value: float | None = None
    threshold_id: UUID | None = None
    status: AlertStatus = AlertStatus.ACTIVE


class AlertUpdate(BaseModel):
    severity: AlertSeverity | None = None
    message: str | None = Field(default=None, min_length=1, max_length=1000)
    status: AlertStatus | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by_user_id: UUID | None = None
    resolved_at: datetime | None = None
    resolution_reason: str | None = Field(default=None, max_length=500)


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    sensor_id: UUID | None
    actuator_id: UUID | None
    alert_type: str
    severity: AlertSeverity
    message: str
    trigger_value: float | None
    threshold_id: UUID | None
    status: AlertStatus
    created_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by_user_id: UUID | None
    resolved_at: datetime | None
    resolution_reason: str | None