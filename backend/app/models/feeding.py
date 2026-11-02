from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UUIDPrimaryKeyMixin, TimestampedMixin, Base, TIMESTAMPTZ
from app.db.enums import FEEDING_EVENT_STATUS_DB, FeedingEventStatus


class FeedingSchedule(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "feeding_schedules"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    actuator_id: Mapped[UUID] = mapped_column(ForeignKey("actuators.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    schedule_expression: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_per_feed_grams: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="feeding_schedules")
    actuator: Mapped["Actuator"] = relationship(back_populates="feeding_schedules")
    feeding_events: Mapped[list["FeedingEvent"]] = relationship(back_populates="schedule")


class FeederCalibration(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feeder_calibrations"

    actuator_id: Mapped[UUID] = mapped_column(ForeignKey("actuators.id", ondelete="RESTRICT"), nullable=False, index=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_seconds: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    measured_grams: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    grams_per_second: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    calibration_method: Mapped[str] = mapped_column(String(100), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    verified_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actuator: Mapped["Actuator"] = relationship(back_populates="feeder_calibrations")
    verified_by_user: Mapped["User | None"] = relationship(back_populates="feeder_calibrations")


class FishPopulationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "fish_population_records"

    tank_id: Mapped[UUID] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=False, index=True)
    species: Mapped[str] = mapped_column(String(150), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_biomass_grams: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    effective_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    recorded_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tank: Mapped["Tank"] = relationship(back_populates="fish_population_records")
    recorded_by_user: Mapped["User | None"] = relationship(back_populates="population_records")


class FeedingEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feeding_events"

    schedule_id: Mapped[UUID | None] = mapped_column(ForeignKey("feeding_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    actuator_event_id: Mapped[UUID] = mapped_column(ForeignKey("actuator_events.id", ondelete="RESTRICT"), nullable=False, unique=True)
    tank_id: Mapped[UUID] = mapped_column(ForeignKey("tanks.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount_grams: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    calculated_from_biomass: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    calibration_id: Mapped[UUID | None] = mapped_column(ForeignKey("feeder_calibrations.id", ondelete="SET NULL"), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    status: Mapped[FeedingEventStatus] = mapped_column(FEEDING_EVENT_STATUS_DB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    schedule: Mapped["FeedingSchedule | None"] = relationship(back_populates="feeding_events")
    actuator_event: Mapped["ActuatorEvent"] = relationship()
    tank: Mapped["Tank"] = relationship(back_populates="feeding_events")
    calibration: Mapped["FeederCalibration | None"] = relationship()
