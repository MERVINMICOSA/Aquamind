"""Authenticated dashboard access to saved USB serial ESP32 telemetry.

No public ESP32 HTTP ingestion endpoint is exposed: the Pi reads
the attached USB device locally in Esp32SerialWorker.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.esp32_telemetry import Esp32Telemetry
from app.schemas.esp32_telemetry import Esp32TelemetryResponse, Esp32TelemetrySearchResponse

router = APIRouter(
    prefix="/esp32", tags=["ESP32 telemetry"],
    dependencies=[Depends(get_current_user)],
)


# Search only supported numeric measurements. The wire protocol may contain
# unverified estimates; deliberately omit them from normal history search.
# Historical pH/TDS values are device claims, never server calibration proof.
HistoricalField = Literal[
    "water_temp_c", "ph", "tds_ppm", "water_level_pct",
    "water_height_cm", "distance_cm", "air_temp_c", "humidity_pct",
]


@router.get(
    "/telemetry/search",
    response_model=Esp32TelemetrySearchResponse,
)
async def search_esp32_telemetry(
    system_id: UUID,
    field: HistoricalField,
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

    # JSON path comes from a strict Literal allowlist, not user-supplied SQL.
    numeric = Esp32Telemetry.packet[field].as_float()
    filters = [
        Esp32Telemetry.system_id == system_id,
        numeric.is_not(None),
    ]
    if start_at is not None:
        filters.append(Esp32Telemetry.received_at >= start_at.astimezone(timezone.utc))
    if end_at is not None:
        filters.append(Esp32Telemetry.received_at < end_at.astimezone(timezone.utc))
    if min_value is not None:
        filters.append(numeric >= min_value)
    if max_value is not None:
        filters.append(numeric <= max_value)

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
) -> Esp32Telemetry | None:
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
