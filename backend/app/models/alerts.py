from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UUIDPrimaryKeyMixin, Base, TIMESTAMPTZ
from app.db.enums import ALERT_SEVERITY_DB, ALERT_STATUS_DB, MEASUREMENT_TYPE_DB, SENSOR_TYPE_DB, AlertSeverity, AlertStatus, MeasurementType, SensorType


class AlertThreshold(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "alert_thresholds"

    sensor_type: Mapped[SensorType] = mapped_column(SENSOR_TYPE_DB, nullable=False, index=True)
    measurement_type: Mapped[MeasurementType] = mapped_column(MEASUREMENT_TYPE_DB, nullable=False)
    warning_low: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    warning_high: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    critical_low: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    critical_high: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=900, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)

    updated_by_user: Mapped["User | None"] = relationship()


class Alert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "alerts"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    sensor_id: Mapped[UUID | None] = mapped_column(ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True, index=True)
    actuator_id: Mapped[UUID | None] = mapped_column(ForeignKey("actuators.id", ondelete="SET NULL"), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(ALERT_SEVERITY_DB, nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    trigger_value: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    threshold_id: Mapped[UUID | None] = mapped_column(ForeignKey("alert_thresholds.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[AlertStatus] = mapped_column(ALERT_STATUS_DB, nullable=False, default=AlertStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    acknowledged_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="alerts")
    sensor: Mapped["Sensor | None"] = relationship()
    actuator: Mapped["Actuator | None"] = relationship()
    threshold: Mapped["AlertThreshold | None"] = relationship()
    acknowledged_by_user: Mapped["User | None"] = relationship(back_populates="alert_acknowledgements")
