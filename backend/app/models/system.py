from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UUIDPrimaryKeyMixin, TimestampedMixin, CreatedAtMixin, SoftDeleteMixin, Base, TIMESTAMPTZ
from app.db.enums import USER_ROLE_DB, UserRole


class User(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(USER_ROLE_DB, default=UserRole.ADMIN, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    settings_updates: Mapped[list["SystemSetting"]] = relationship(back_populates="updated_by_user")
    calibration_verifications: Mapped[list["SensorCalibration"]] = relationship(back_populates="verified_by_user")
    feeder_calibrations: Mapped[list["FeederCalibration"]] = relationship(back_populates="verified_by_user")
    population_records: Mapped[list["FishPopulationRecord"]] = relationship(back_populates="recorded_by_user")
    alert_acknowledgements: Mapped[list["Alert"]] = relationship(back_populates="acknowledged_by_user")
    ai_reviews: Mapped[list["AIRecommendation"]] = relationship(back_populates="reviewed_by_user")


class RefreshToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class AquaponicsSystem(
    UUIDPrimaryKeyMixin,
    TimestampedMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "aquaponics_systems"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    settings: Mapped[list["SystemSetting"]] = relationship(back_populates="system", cascade="all, delete-orphan")
    tanks: Mapped[list["Tank"]] = relationship(back_populates="system", cascade="all, delete-orphan")
    grow_beds: Mapped[list["GrowBed"]] = relationship(back_populates="system", cascade="all, delete-orphan")
    reservoirs: Mapped[list["Reservoir"]] = relationship(back_populates="system", cascade="all, delete-orphan")
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="system", cascade="all, delete-orphan")
    actuators: Mapped[list["Actuator"]] = relationship(back_populates="system", cascade="all, delete-orphan")
    automation_rules: Mapped[list["AutomationRule"]] = relationship(back_populates="system", cascade="all, delete-orphan")
    feeding_schedules: Mapped[list["FeedingSchedule"]] = relationship(back_populates="system", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="system")
    system_events: Mapped[list["SystemEvent"]] = relationship(back_populates="system")
    ai_recommendations: Mapped[list["AIRecommendation"]] = relationship(back_populates="system")
    sync_records: Mapped[list["SyncRecord"]] = relationship(back_populates="system")


class SystemSetting(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "system_settings"
    __table_args__ = (UniqueConstraint("system_id", "setting_key", name="uq_system_settings_system_key"),)

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    setting_key: Mapped[str] = mapped_column(String(150), nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="settings")
    updated_by_user: Mapped["User | None"] = relationship(back_populates="settings_updates", foreign_keys=[updated_by_user_id])


class Tank(UUIDPrimaryKeyMixin, TimestampedMixin, SoftDeleteMixin, Base):
    __tablename__ = "tanks"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity_liters: Mapped[float] = mapped_column(nullable=False)
    species: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="tanks")
    fish_population_records: Mapped[list["FishPopulationRecord"]] = relationship(back_populates="tank", cascade="all, delete-orphan")
    feeding_events: Mapped[list["FeedingEvent"]] = relationship(back_populates="tank")
    refill_events: Mapped[list["RefillEvent"]] = relationship(back_populates="target_tank")


class GrowBed(UUIDPrimaryKeyMixin, TimestampedMixin, SoftDeleteMixin, Base):
    __tablename__ = "grow_beds"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    crop_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="grow_beds")


class Reservoir(UUIDPrimaryKeyMixin, TimestampedMixin, SoftDeleteMixin, Base):
    __tablename__ = "reservoirs"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity_liters: Mapped[float] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="reservoirs")
    refill_events: Mapped[list["RefillEvent"]] = relationship(back_populates="reservoir")


# Forward references are resolved by SQLAlchemy after all model modules are imported.
