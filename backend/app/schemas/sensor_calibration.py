from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.enums import CalibrationStatus


class SensorCalibrationCreate(BaseModel):
    sensor_id: UUID
    offset: float
    factor: float
    calibration_data: dict | None = None
    performed_at: datetime
    verified_by_user_id: UUID | None = None
    status: CalibrationStatus
    notes: str | None = None


class SensorCalibrationUpdate(BaseModel):
    offset: float | None = None
    factor: float | None = None
    calibration_data: dict | None = None
    performed_at: datetime | None = None
    verified_by_user_id: UUID | None = None
    status: CalibrationStatus | None = None
    notes: str | None = None


class SensorCalibrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sensor_id: UUID
    offset: float
    factor: float
    calibration_data: dict | None
    performed_at: datetime
    verified_by_user_id: UUID | None
    status: CalibrationStatus
    notes: str | None
    created_at: datetime