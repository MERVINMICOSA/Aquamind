from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UUIDPrimaryKeyMixin, TimestampedMixin, CreatedAtMixin, SoftDeleteMixin, Base, TIMESTAMPTZ
from app.db.enums import (
    ACTUATOR_COMMAND_TYPE_DB, ACTUATOR_STATE_DB, ACTUATOR_TYPE_DB, CONTROL_MODE_DB,
    EXECUTION_STATUS_DB, LOCATION_TYPE_DB, TRIGGER_SOURCE_DB,
    ActuatorCommandType, ActuatorState, ActuatorType, ControlMode, ExecutionStatus, LocationType, TriggerSource,
)


class Actuator(UUIDPrimaryKeyMixin, TimestampedMixin, SoftDeleteMixin, Base):
    __tablename__ = "actuators"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    actuator_type: Mapped[ActuatorType] = mapped_column(ACTUATOR_TYPE_DB, nullable=False, index=True)
    control_mode: Mapped[ControlMode] = mapped_column(CONTROL_MODE_DB, nullable=False)
    hardware_identifier: Mapped[str | None] = mapped_column(String(150), nullable=True, unique=True)
    location_type: Mapped["LocationType | None"] = mapped_column(LOCATION_TYPE_DB, nullable=True)
    location_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    safety_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    current_state: Mapped[ActuatorState] = mapped_column(ACTUATOR_STATE_DB, nullable=False, default=ActuatorState.OFF)
    current_value: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    last_state_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="actuators")
    events: Mapped[list["ActuatorEvent"]] = relationship(back_populates="actuator")
    feeder_calibrations: Mapped[list["FeederCalibration"]] = relationship(back_populates="actuator")
    feeding_schedules: Mapped[list["FeedingSchedule"]] = relationship(back_populates="actuator")


class ActuatorEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "actuator_events"

    actuator_id: Mapped[UUID] = mapped_column(ForeignKey("actuators.id", ondelete="RESTRICT"), nullable=False, index=True)
    command_type: Mapped[ActuatorCommandType] = mapped_column(ACTUATOR_COMMAND_TYPE_DB, nullable=False)
    requested_value: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    actual_value: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trigger_source: Mapped[TriggerSource] = mapped_column(TRIGGER_SOURCE_DB, nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(EXECUTION_STATUS_DB, nullable=False)
    fault_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    actuator: Mapped["Actuator"] = relationship(back_populates="events")
