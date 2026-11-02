from __future__ import annotations

from datetime import datetime, timezone
from hmac import compare_digest
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.core.config import settings
from app.models.esp32_telemetry import Esp32Telemetry
from app.models.system import AquaponicsSystem
from app.schemas.esp32_telemetry import Esp32SensorPacket, Esp32TelemetryResponse


router = APIRouter(prefix="/esp32", tags=["ESP32 telemetry"])


def _ingest_configuration() -> UUID:
    """Fail closed when there is no configured device identity or secret."""
    if (
        len(settings.ESP32_INGEST_TOKEN) < 32
        or not settings.ESP32_DEVICE_ID
        or not settings.ESP32_SYSTEM_ID
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 ingestion is not configured",
        )
    try:
        return UUID(settings.ESP32_SYSTEM_ID)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 ingestion system is not configured",
        ) from exc


def require_esp32_device(
    device_token: str | None = Header(default=None, alias="X-ESP32-Token"),
) -> UUID:
    """Authenticates device ingestion independently of admin JWT sessions."""
    system_id = _ingest_configuration()
    if device_token is None or not compare_digest(
        device_token.encode("utf-8"), settings.ESP32_INGEST_TOKEN.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device token",
        )
    return system_id


def _same_packet(row: Esp32Telemetry, packet: dict) -> bool:
    return row.packet == packet


@router.post(
    "/telemetry",
    response_model=Esp32TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_esp32_telemetry(
    payload: Esp32SensorPacket,
    response: Response,
    system_id: UUID = Depends(require_esp32_device),
    session: AsyncSession = Depends(get_db_session),
) -> Esp32Telemetry:
    """Persist an entire v1 packet. This path cannot command any actuators.

    POST uses a device-specific shared secret, not an admin JWT.
    Calibration guesses are stored as telemetry ONLY, never as validated
    sensor_readings that could trigger alert/automation pathways.
    """
    if payload.device_id != settings.ESP32_DEVICE_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device not authorized",
        )

    system = await session.get(AquaponicsSystem, system_id)
    if system is None or system.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configured ESP32 system is not available",
        )

    contents = payload.model_dump(mode="json")
    identity = (
        Esp32Telemetry.system_id == system_id,
        Esp32Telemetry.device_id == payload.device_id,
        Esp32Telemetry.sequence == payload.sequence,
        Esp32Telemetry.uptime_ms == payload.uptime_ms,
    )
    existing = (
        await session.execute(select(Esp32Telemetry).where(*identity))
    ).scalar_one_or_none()
    if existing is not None:
        if not _same_packet(existing, contents):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Packet identity already used for different data",
            )
        response.status_code = status.HTTP_200_OK
        return existing

    row = Esp32Telemetry(
        received_at=datetime.now(timezone.utc),
        system_id=system_id,
        device_id=payload.device_id,
        sequence=payload.sequence,
        uptime_ms=payload.uptime_ms,
        packet=contents,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        # A concurrent identical retransmission can race the first insert.
        await session.rollback()
        existing = (
            await session.execute(select(Esp32Telemetry).where(*identity))
        ).scalar_one_or_none()
        if existing is not None and _same_packet(existing, contents):
            response.status_code = status.HTTP_200_OK
            return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Packet identity conflict",
        ) from None

    await session.refresh(row)
    return row


@router.get(
    "/telemetry/latest",
    response_model=Esp32TelemetryResponse | None,
    dependencies=[Depends(get_current_user)],
)
async def latest_esp32_telemetry(
    system_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Esp32Telemetry | None:
    """Return latest received packet, or null when no packets exist."""
    query = (
        select(Esp32Telemetry)
        .where(Esp32Telemetry.system_id == system_id)
        .order_by(
            Esp32Telemetry.received_at.desc(),
            Esp32Telemetry.id.desc(),
        )
        .limit(1)
    )
    return (await session.execute(query)).scalar_one_or_none()


@router.get(
    "/telemetry",
    response_model=list[Esp32TelemetryResponse],
    dependencies=[Depends(get_current_user)],
)
async def history_esp32_telemetry(
    system_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[Esp32Telemetry]:
    """Bounded persisted packet history for the protected dashboard."""
    query = (
        select(Esp32Telemetry)
        .where(Esp32Telemetry.system_id == system_id)
        .order_by(
            Esp32Telemetry.received_at.desc(),
            Esp32Telemetry.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list((await session.execute(query)).scalars().all())
