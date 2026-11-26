"""Authenticated dashboard access to saved USB serial ESP32 telemetry.

No public ESP32 HTTP ingestion endpoint is exposed: the Pi reads
the attached USB device locally in Esp32SerialWorker.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session, require_admin
from app.models.esp32_capture import Esp32CaptureState
from app.models.esp32_telemetry import Esp32Telemetry
from app.models.system import AquaponicsSystem, User
from app.models.other import AuditLog
from app.schemas.esp32_telemetry import (
    Esp32TelemetryResponse, Esp32TelemetrySearchResponse,
    Esp32CaptureUpdate, Esp32CaptureResponse,
)

router = APIRouter(
    prefix="/esp32", tags=["ESP32 telemetry"],
    dependencies=[Depends(get_current_user)],
)


def _capture_view(system_id: UUID, state: Esp32CaptureState | None) -> dict:
    if state is None:
        return {"system_id": system_id, "mode": "live", "interval_minutes": 5}
    return {
        "system_id": system_id,
        "device_id": state.device_id,
        "mode": state.mode,
        "interval_minutes": state.interval_minutes,
        "latest_received_at": state.latest_received_at,
        "last_saved_at": state.last_saved_at,
        "last_saved_scheduled_at": state.last_saved_scheduled_at,
        "next_save_at": state.next_save_at,
    }


async def _check_system(session: AsyncSession, system_id: UUID) -> None:
    system = await session.get(AquaponicsSystem, system_id)
    if system is None or system.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Aquaponics system not found")


@router.get("/capture", response_model=Esp32CaptureResponse)
async def get_esp32_capture(
    system_id: UUID, session: AsyncSession = Depends(get_db_session),
) -> dict:
    await _check_system(session, system_id)
    state = await session.get(Esp32CaptureState, system_id)
    return _capture_view(system_id, state)


@router.put(
    "/capture", response_model=Esp32CaptureResponse,
    dependencies=[Depends(require_admin)],
)
async def update_esp32_capture(
    system_id: UUID,
    update: Esp32CaptureUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Only administrators may change collection; never accepts arbitrary keys."""
    await _check_system(session, system_id)
    state = await session.get(Esp32CaptureState, system_id, with_for_update=True)
    if state is None:
        state = Esp32CaptureState(system_id=system_id, mode="live", interval_minutes=5)
        session.add(state)

    if state.mode != update.mode or state.interval_minutes != update.interval_minutes:
        now = datetime.now(timezone.utc)
        state.mode = update.mode
        state.interval_minutes = update.interval_minutes
        # A changed setting starts a NEW interval. Old packets cannot count
        # toward it, and the timer never fabricates a missed reading.
        state.window_started_at = now if update.mode == "timed" else None
        state.next_save_at = (
            now + timedelta(minutes=update.interval_minutes)
            if update.mode == "timed" else None
        )
    await session.commit()
    await session.refresh(state)
    return _capture_view(system_id, state)


# Search only supported numeric measurements. The wire protocol may contain
# unverified estimates; deliberately omit them from normal history search.
# Historical pH/TDS values are device claims, never server calibration proof.
HistoricalField = Literal[
    "all", "water_temp_c", "ph", "tds_ppm", "water_level_pct",
    "water_height_cm", "distance_cm", "air_temp_c", "humidity_pct",
]


@router.get(
    "/telemetry/search",
    response_model=Esp32TelemetrySearchResponse,
)
async def search_esp32_telemetry(
    system_id: UUID,
    field: HistoricalField = "all",
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    min_value: float | None = Query(default=None, allow_inf_nan=False),
    max_value: float | None = Query(default=None, allow_inf_nan=False),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1000000),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Authenticated, system-scoped search of all archived ESP32 measurements.

    The timestamp filter applies to the server's packet-receipt time; firmware
    does not supply a reliable UTC clock in v1. Date range is [start, end).
    "all" returns complete archived packets, with missing fields preserved.
    Results are deterministically ordered newest first, with a total count.
    """
    for name, value in (("start_at", start_at), ("end_at", end_at)):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{name} must include a timezone offset",
            )
    if start_at is not None and end_at is not None and start_at >= end_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_at must be earlier than end_at",
        )
    if min_value is not None and max_value is not None and min_value > max_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_value must be less than or equal to max_value",
        )

    # "all" shows all stored packets for the system, including packets where
    # some probes returned null. Never put a user-supplied SQL key into JSON.
    filters = [Esp32Telemetry.system_id == system_id]
    numeric = None
    if field != "all":
        numeric = Esp32Telemetry.packet[field].as_float()
        filters.append(numeric.is_not(None))
    if start_at is not None:
        filters.append(Esp32Telemetry.received_at >= start_at.astimezone(timezone.utc))
    if end_at is not None:
        filters.append(Esp32Telemetry.received_at < end_at.astimezone(timezone.utc))
    if min_value is not None and numeric is not None:
        filters.append(numeric >= min_value)
    if max_value is not None and numeric is not None:
        filters.append(numeric <= max_value)
    if field == "all" and (min_value is not None or max_value is not None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Value filters require an individual sensor field",
        )

    total = (
        await session.execute(
            select(func.count()).select_from(Esp32Telemetry).where(*filters)
        )
    ).scalar_one()

    rows = (
        await session.execute(
            select(Esp32Telemetry)
            .where(*filters)
            .order_by(Esp32Telemetry.received_at.desc(), Esp32Telemetry.id.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return {
        "items": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
    }



@router.get(
    "/telemetry/latest",
    response_model=Esp32TelemetryResponse | None,
)
async def latest_esp32_telemetry(
    system_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Esp32Telemetry | dict | None:
    # Current monitoring must not depend on the selected archive frequency.
    state = await session.get(Esp32CaptureState, system_id)
    if (
        state is not None and state.latest_packet is not None
        and state.latest_received_at is not None
        and state.latest_packet_id is not None
    ):
        return {
            "id": state.latest_packet_id,
            "system_id": system_id,
            "received_at": state.latest_received_at,
            "packet": state.latest_packet,
        }
    # Upgrade compatibility: show pre-migration archived packets until
    # the first new USB packet is received.
    query = (
        select(Esp32Telemetry)
        .where(Esp32Telemetry.system_id == system_id)
        .order_by(Esp32Telemetry.received_at.desc(), Esp32Telemetry.id.desc())
        .limit(1)
    )
    return (await session.execute(query)).scalar_one_or_none()


@router.get(
    "/telemetry",
    response_model=list[Esp32TelemetryResponse],
)
async def history_esp32_telemetry(
    system_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[Esp32Telemetry]:
    query = (
        select(Esp32Telemetry)
        .where(Esp32Telemetry.system_id == system_id)
        .order_by(Esp32Telemetry.received_at.desc(), Esp32Telemetry.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list((await session.execute(query)).scalars().all())


# Corrections are separate operator assertions, never firmware measurements.
# The existing audit_logs table provides append-only application-level history.
CorrectionField = Literal[
    "water_temp_c", "ph", "tds_ppm", "water_level_pct",
    "water_height_cm", "distance_cm", "air_temp_c", "humidity_pct",
]
_CORRECTION_BOUNDS = {
    "water_temp_c": (-10, 90), "ph": (0, 14), "tds_ppm": (0, 100000),
    "water_level_pct": (0, 100), "water_height_cm": (0, 100000),
    "distance_cm": (0, 100000), "air_temp_c": (-50, 90),
    "humidity_pct": (0, 100),
}
_CORRECTION_RAW_KEYS = {
    "water_temp_c": "water_temperature", "ph": "ph", "tds_ppm": "tds",
    "water_level_pct": "ultrasonic", "water_height_cm": "ultrasonic",
    "distance_cm": "ultrasonic", "air_temp_c": "air_temperature",
    "humidity_pct": "humidity",
}


class HistoryCorrectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    field: CorrectionField
    corrected_value: float
    reason: str = Field(min_length=1, max_length=1000)
    evidence: str = Field(min_length=1, max_length=1000)

    @field_validator("reason", "evidence", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class HistoryCorrectionResponse(BaseModel):
    id: UUID
    field: CorrectionField
    original_value: float
    corrected_value: float
    reason: str
    evidence: str
    recorded_by: str
    created_at: datetime


def _correction_view(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "field": log.new_value["field"],
        "original_value": log.old_value["value"],
        "corrected_value": log.new_value["value"],
        "reason": log.new_value["reason"],
        "evidence": log.new_value["evidence"],
        "recorded_by": log.new_value["recorded_by"],
        "created_at": log.created_at,
    }


async def _correction_packet(
    session: AsyncSession, system_id: UUID, packet_id: UUID,
) -> Esp32Telemetry:
    await _check_system(session, system_id)
    packet = await session.get(Esp32Telemetry, packet_id)
    if packet is None or packet.system_id != system_id:
        raise HTTPException(status_code=404, detail="Saved packet not found")
    return packet


@router.get(
    "/telemetry/{packet_id}/corrections",
    response_model=list[HistoryCorrectionResponse],
)
async def list_history_corrections(
    packet_id: UUID, system_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    await _correction_packet(session, system_id, packet_id)
    logs = (await session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "esp32_telemetry",
            AuditLog.entity_id == packet_id,
            AuditLog.action == "propose_history_correction",
        ).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(100)
    )).scalars().all()
    return [_correction_view(log) for log in logs]


@router.post(
    "/telemetry/{packet_id}/corrections",
    response_model=HistoryCorrectionResponse,
    status_code=201,
)
async def propose_history_correction(
    packet_id: UUID, system_id: UUID, correction: HistoryCorrectionInput,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
) -> dict:
    item = await _correction_packet(session, system_id, packet_id)
    field = correction.field
    low, high = _CORRECTION_BOUNDS[field]
    if not low <= correction.corrected_value <= high:
        raise HTTPException(status_code=422, detail="Value outside sensor's supported numerical bounds")
    original = item.packet.get(field)
    raw = (item.packet.get("raw_readings") or {}).get(_CORRECTION_RAW_KEYS[field])
    if (
        type(original) not in (int, float)
        or not low <= original <= high
        or (raw is not None and raw.get("status") != "ok")
        or (field == "ph" and not item.packet.get("ph_calibrated"))
        or (field == "tds_ppm" and not item.packet.get("tds_calibrated"))
    ):
        raise HTTPException(status_code=422, detail="Missing or failed measurements cannot be replaced")
    if original == correction.corrected_value:
        raise HTTPException(status_code=422, detail="Correction must differ from original value")
    log = AuditLog(
        user_id=admin.id, action="propose_history_correction",
        entity_type="esp32_telemetry", entity_id=item.id,
        old_value={"field": field, "value": original, "received_at": item.received_at.isoformat(),
                   "device_id": item.device_id, "sequence": item.sequence, "uptime_ms": item.uptime_ms},
        new_value={"field": field, "value": correction.corrected_value,
                   "reason": correction.reason, "evidence": correction.evidence,
                   "recorded_by": admin.username, "system_id": str(system_id)},
        source="manual_validation", created_at=datetime.now(timezone.utc),
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return _correction_view(log)
