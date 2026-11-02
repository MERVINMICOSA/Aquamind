from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import MeasurementType, SensorType


class AlertThresholdCreate(BaseModel):
    sensor_type: SensorType
    measurement_type: MeasurementType

    warning_low: float | None = None
    warning_high: float | None = None
    critical_low: float | None = None
    critical_high: float | None = None

    cooldown_seconds: int = Field(default=900, ge=0)
    enabled: bool = True
    updated_by_user_id: UUID | None = None


class AlertThresholdUpdate(BaseModel):
    sensor_type: SensorType | None = None
    measurement_type: MeasurementType | None = None

    warning_low: float | None = None
    warning_high: float | None = None
    critical_low: float | None = None
    critical_high: float | None = None

    cooldown_seconds: int | None = Field(default=None, ge=0)
    enabled: bool | None = None
    updated_by_user_id: UUID | None = None


class AlertThresholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sensor_type: SensorType
    measurement_type: MeasurementType

    warning_low: float | None
    warning_high: float | None
    critical_low: float | None
    critical_high: float | None

    cooldown_seconds: int
    enabled: bool
    updated_by_user_id: UUID | None
    updated_at: datetime
