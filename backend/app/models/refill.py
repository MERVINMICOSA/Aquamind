from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UUIDPrimaryKeyMixin, CreatedAtMixin, Base, TIMESTAMPTZ
from app.db.enums import EXECUTION_STATUS_DB, REFILL_TRIGGER_DB, ExecutionStatus, RefillTrigger


class RefillEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "refill_events"

    reservoir_id: Mapped[UUID] = mapped_column(ForeignKey("reservoirs.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_tank_id: Mapped[UUID] = mapped_column(ForeignKey("tanks.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_level_percent: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    end_level_percent: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    trigger: Mapped[RefillTrigger] = mapped_column(REFILL_TRIGGER_DB, nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(EXECUTION_STATUS_DB, nullable=False)
    timeout_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    reservoir: Mapped["Reservoir"] = relationship(back_populates="refill_events")
    target_tank: Mapped["Tank"] = relationship(back_populates="refill_events")
