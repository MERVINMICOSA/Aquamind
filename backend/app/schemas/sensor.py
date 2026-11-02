from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import CalibrationStatus, LocationType, MeasurementType, SensorType


class SensorCreate(BaseModel):
    system_id: UUID
    name: str = Field(min_length=1, max_length=100)
    sensor_type: SensorType
    measurement_type: MeasurementType
    location_type: LocationType
    location_id: UUID | None = None
    unit: str = Field(min_length=1, max_length=32)
    hardware_identifier: str | None = Field(default=None, max_length=150)
    is_simulated: bool = False
    is_enabled: bool = True
    sampling_interval_seconds: int = Field(gt=0)
    calibration_status: CalibrationStatus = CalibrationStatus.PENDING


class SensorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    sensor_type: SensorType | None = None
    measurement_type: MeasurementType | None = None
    location_type: LocationType | None = None
    location_id: UUID | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    hardware_identifier: str | None = Field(default=None, max_length=150)
    is_simulated: bool | None = None
    is_enabled: bool | None = None
    sampling_interval_seconds: int | None = Field(default=None, gt=0)
    calibration_status: CalibrationStatus | None = None


class SensorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    name: str
    sensor_type: SensorType
    measurement_type: MeasurementType
    location_type: LocationType
    location_id: UUID | None
    unit: str
    hardware_identifier: str | None
    is_simulated: bool
    is_enabled: bool
    sampling_interval_seconds: int
    calibration_status: CalibrationStatus
    created_at: datetime
    updated_at: datetime
