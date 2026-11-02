from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import FeedingEventStatus


# =========================================================
# Feeding Schedule
# =========================================================

class FeedingScheduleCreate(BaseModel):
    system_id: UUID
    actuator_id: UUID
    name: str = Field(min_length=1, max_length=150)
    schedule_expression: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    max_per_feed_grams: float = Field(gt=0)


class FeedingScheduleUpdate(BaseModel):
    actuator_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    schedule_expression: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    enabled: bool | None = None
    max_per_feed_grams: float | None = Field(default=None, gt=0)


class FeedingScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    actuator_id: UUID
    name: str
    schedule_expression: str
    enabled: bool
    max_per_feed_grams: float
    created_at: datetime
    updated_at: datetime


# =========================================================
# Feeder Calibration
# =========================================================

class FeederCalibrationCreate(BaseModel):
    actuator_id: UUID
    run_count: int = Field(gt=0)
    measured_seconds: float = Field(gt=0)
    measured_grams: float = Field(gt=0)
    grams_per_second: float = Field(gt=0)
    calibration_method: str = Field(min_length=1, max_length=100)
    performed_at: datetime
    verified_by_user_id: UUID | None = None
    notes: str | None = None


class FeederCalibrationUpdate(BaseModel):
    run_count: int | None = Field(default=None, gt=0)
    measured_seconds: float | None = Field(default=None, gt=0)
    measured_grams: float | None = Field(default=None, gt=0)
    grams_per_second: float | None = Field(default=None, gt=0)
    calibration_method: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    performed_at: datetime | None = None
    verified_by_user_id: UUID | None = None
    notes: str | None = None


class FeederCalibrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actuator_id: UUID
    run_count: int
    measured_seconds: float
    measured_grams: float
    grams_per_second: float
    calibration_method: str
    performed_at: datetime
    verified_by_user_id: UUID | None
    notes: str | None


# =========================================================
# Fish Population Record
# =========================================================

class FishPopulationRecordCreate(BaseModel):
    tank_id: UUID
    species: str = Field(min_length=1, max_length=150)
    count: int = Field(ge=0)
    estimated_biomass_grams: float | None = Field(
        default=None,
        ge=0,
    )
    effective_at: datetime
    recorded_by_user_id: UUID | None = None
    notes: str | None = None


class FishPopulationRecordUpdate(BaseModel):
    species: str | None = Field(default=None, min_length=1, max_length=150)
    count: int | None = Field(default=None, ge=0)
    estimated_biomass_grams: float | None = Field(
        default=None,
        ge=0,
    )
    effective_at: datetime | None = None
    recorded_by_user_id: UUID | None = None
    notes: str | None = None


class FishPopulationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tank_id: UUID
    species: str
    count: int
    estimated_biomass_grams: float | None
    effective_at: datetime
    recorded_by_user_id: UUID | None
    notes: str | None


# =========================================================
# Feeding Event
# =========================================================

class FeedingEventCreate(BaseModel):
    schedule_id: UUID | None = None
    actuator_event_id: UUID
    tank_id: UUID
    amount_grams: float = Field(gt=0)
    duration_seconds: float = Field(gt=0)
    calculated_from_biomass: float | None = Field(
        default=None,
        ge=0,
    )
    calibration_id: UUID | None = None
    executed_at: datetime
    status: FeedingEventStatus
    notes: str | None = None


class FeedingEventUpdate(BaseModel):
    amount_grams: float | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, gt=0)
    calculated_from_biomass: float | None = Field(
        default=None,
        ge=0,
    )
    calibration_id: UUID | None = None
    executed_at: datetime | None = None
    status: FeedingEventStatus | None = None
    notes: str | None = None


class FeedingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schedule_id: UUID | None
    actuator_event_id: UUID
    tank_id: UUID
    amount_grams: float
    duration_seconds: float
    calculated_from_biomass: float | None
    calibration_id: UUID | None
    executed_at: datetime
    status: FeedingEventStatus
    notes: str | None