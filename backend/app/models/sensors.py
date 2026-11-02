from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    UUIDPrimaryKeyMixin,
    TimestampedMixin,
    CreatedAtMixin,
    SoftDeleteMixin,
    Base,
    TIMESTAMPTZ,
)
from app.db.enums import (
    CALIBRATION_STATUS_DB, LOCATION_TYPE_DB, MEASUREMENT_TYPE_DB,
    READING_QUALITY_DB, READING_SOURCE_DB, SENSOR_TYPE_DB,
    CalibrationStatus, LocationType, MeasurementType, ReadingQuality, ReadingSource, SensorType,
)


class Sensor(
    UUIDPrimaryKeyMixin,
    TimestampedMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "sensors"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(SENSOR_TYPE_DB, nullable=False, index=True)
    measurement_type: Mapped[MeasurementType] = mapped_column(MEASUREMENT_TYPE_DB, nullable=False)
    location_type: Mapped[LocationType] = mapped_column(LOCATION_TYPE_DB, nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    hardware_identifier: Mapped[str | None] = mapped_column(String(150), nullable=True, unique=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sampling_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    calibration_status: Mapped[CalibrationStatus] = mapped_column(CALIBRATION_STATUS_DB, nullable=False, default=CalibrationStatus.PENDING)
    system: Mapped["AquaponicsSystem"] = relationship(back_populates="sensors")
    calibrations: Mapped[list["SensorCalibration"]] = relationship(back_populates="sensor", cascade="all, delete-orphan")
    readings: Mapped[list["SensorReading"]] = relationship(back_populates="sensor")


class SensorCalibration(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "sensor_calibrations"

    sensor_id: Mapped[UUID] = mapped_column(ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True)
    offset: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    factor: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    calibration_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    performed_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    verified_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[CalibrationStatus] = mapped_column(CALIBRATION_STATUS_DB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sensor: Mapped["Sensor"] = relationship(back_populates="calibrations")
    verified_by_user: Mapped["User | None"] = relationship(back_populates="calibration_verifications")


class SensorReading(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        Index("ix_sensor_readings_sensor_recorded_at", "sensor_id", "recorded_at"),
        Index("ix_sensor_readings_recorded_at", "recorded_at"),
    )

    sensor_id: Mapped[UUID] = mapped_column(ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    value_numeric: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_status: Mapped[ReadingQuality] = mapped_column(READING_QUALITY_DB, nullable=False)
    source: Mapped[ReadingSource] = mapped_column(READING_SOURCE_DB, nullable=False)
    sequence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    sensor: Mapped["Sensor"] = relationship(back_populates="readings")
