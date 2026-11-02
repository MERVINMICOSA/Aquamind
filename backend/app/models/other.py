from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UUIDPrimaryKeyMixin, Base, TIMESTAMPTZ
from app.db.enums import RECOMMENDATION_STATUS_DB, SYNC_STATUS_DB, SYSTEM_EVENT_SEVERITY_DB, RecommendationStatus, SyncStatus, SystemEventSeverity


class SystemEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "system_events"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[SystemEventSeverity] = mapped_column(SYSTEM_EVENT_SEVERITY_DB, nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, index=True)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="system_events")


class AIRecommendation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_recommendations"

    system_id: Mapped[UUID] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(RECOMMENDATION_STATUS_DB, nullable=False, default=RecommendationStatus.PENDING_REVIEW)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    approval_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_action_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    system: Mapped["AquaponicsSystem"] = relationship(back_populates="ai_recommendations")
    reviewed_by_user: Mapped["User | None"] = relationship(back_populates="ai_reviews")


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, index=True)

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")


class SyncRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sync_records"

    system_id: Mapped[UUID | None] = mapped_column(ForeignKey("aquaponics_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    source_device_id: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    local_record_id: Mapped[UUID] = mapped_column(nullable=False)
    remote_record_id: Mapped[UUID | None] = mapped_column(nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, index=True)
    synced_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    sync_status: Mapped[SyncStatus] = mapped_column(SYNC_STATUS_DB, nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    system: Mapped["AquaponicsSystem | None"] = relationship(back_populates="sync_records")
