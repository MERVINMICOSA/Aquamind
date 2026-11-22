"""Persistent current ESP32 packet and archive scheduling state."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Esp32CaptureState(Base):
    """One serial source per system; bounded live state, separate archive."""

    __tablename__ = "esp32_capture_state"

    system_id: Mapped[UUID] = mapped_column(
        ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), primary_key=True
    )
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mode: Mapped[str] = mapped_column(String(12), nullable=False, default="live")
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    window_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_save_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_saved_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_packet_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    latest_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latest_uptime_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    latest_packet: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latest_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
