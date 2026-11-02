"""Authenticated dashboard access to saved USB serial ESP32 telemetry.

No public ESP32 HTTP ingestion endpoint is exposed: the Pi reads
the attached USB device locally in Esp32SerialWorker.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.esp32_telemetry import Esp32Telemetry
from app.schemas.esp32_telemetry import Esp32TelemetryResponse

router = APIRouter(
    prefix="/esp32", tags=["ESP32 telemetry"],
    dependencies=[Depends(get_current_user)],
)


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
