from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class Esp32Telemetry(UUIDPrimaryKeyMixin, Base):
    """One complete ESP32 packet, preserved without fabricating sensor readings."""

    __tablename__ = "esp32_telemetry"
    __table_args__ = (
        UniqueConstraint(
            "system_id", "device_id", "sequence", "uptime_ms",
            name="uq_esp32_telemetry_identity",
        ),
        Index("ix_esp32_telemetry_system_received", "system_id", "received_at"),
    )

    system_id: Mapped[UUID] = mapped_column(
        ForeignKey("aquaponics_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    uptime_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    packet: Mapped[dict] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
