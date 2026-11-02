from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UUIDPrimaryKeyMixin, TimestampedMixin, Base, TIMESTAMPTZ
from app.db.enums import AUTOMATION_TRIGGER_TYPE_DB, EXECUTION_STATUS_DB, AutomationTriggerType, ExecutionStatus


class AutomationRule(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "automation_rules"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[AutomationTriggerType] = mapped_column(AUTOMATION_TRIGGER_TYPE_DB, nullable=False)
    condition_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    action_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="automation_rules")
    runs: Mapped[list["AutomationRun"]] = relationship(back_populates="rule", cascade="all, delete-orphan")


class AutomationRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "automation_runs"

    rule_id: Mapped[UUID] = mapped_column(ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    trigger_value: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[ExecutionStatus] = mapped_column(EXECUTION_STATUS_DB, nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule: Mapped["AutomationRule"] = relationship(back_populates="runs")
