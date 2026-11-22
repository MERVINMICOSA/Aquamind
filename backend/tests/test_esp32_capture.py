"""Timed ESP32 persistence must not be confused with live reception."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.esp32_capture import Esp32CaptureState
from app.models.esp32_telemetry import Esp32Telemetry
from app.schemas.esp32_telemetry import Esp32SensorPacket
from app.services.esp32_serial_service import (
    flush_esp32_interval, persist_esp32_packet,
)

BASE = {
    "type": "aquamind_sensor",
    "schema_version": 1,
    "device_id": "esp32-devkit-01",
    "sequence": 1,
    "uptime_ms": 1000,
    "ph_calibrated": False,
    "tds_calibrated": False,
    "water_temp_c": 27.5,
    "water_level_pct": None,
}
T0 = datetime(2026, 11, 22, 10, 0, 0, tzinfo=timezone.utc)


async def make_system(client) -> UUID:
    response = await client.post(
        "/api/v1/systems",
        json={"name": "Capture test", "timezone": "UTC", "is_active": True},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def packet(sequence: int, *, temperature: float = 27.5) -> Esp32SensorPacket:
    return Esp32SensorPacket.model_validate({
        **BASE, "sequence": sequence, "uptime_ms": sequence * 1000,
        "water_temp_c": temperature,
    })


async def accept(factory, system_id: UUID, sequence: int, at: datetime, temperature: float = 27.5):
    return await persist_esp32_packet(
        factory, system_id=system_id, expected_device_id="esp32-devkit-01",
        packet=packet(sequence, temperature=temperature), received_at=at,
    )


async def set_timed(factory, system_id: UUID, *, minutes=1):
    async with factory() as session:
        session.add(Esp32CaptureState(
            system_id=system_id, mode="timed", interval_minutes=minutes,
            window_started_at=T0, next_save_at=T0 + timedelta(minutes=minutes),
        ))
        await session.commit()


async def stored(factory):
    async with factory() as session:
        return list((await session.execute(
            select(Esp32Telemetry).order_by(Esp32Telemetry.received_at)
        )).scalars().all())


@pytest.mark.asyncio
async def test_live_saves_every_distinct_packet_and_deduplicates(client, test_session_factory):
    system_id = await make_system(client)
    assert await accept(test_session_factory, system_id, 1, T0) == "created"
    assert await accept(test_session_factory, system_id, 2, T0 + timedelta(seconds=2)) == "created"
    assert await accept(test_session_factory, system_id, 2, T0 + timedelta(seconds=3)) == "duplicate"
    assert len(await stored(test_session_factory)) == 2
    latest = await client.get("/api/v1/esp32/telemetry/latest", params={"system_id": str(system_id)})
    assert latest.status_code == 200
    assert latest.json()["packet"]["sequence"] == 2
    config = await client.get("/api/v1/esp32/capture", params={"system_id": str(system_id)})
    assert config.json()["mode"] == "live"


@pytest.mark.asyncio
async def test_timed_selects_last_pre_boundary_packet_without_duplicate(client, test_session_factory):
    system_id = await make_system(client)
    await set_timed(test_session_factory, system_id)
    await accept(test_session_factory, system_id, 1, T0 + timedelta(seconds=1), 20.0)
    await accept(test_session_factory, system_id, 2, T0 + timedelta(seconds=58), 25.0)
    assert await stored(test_session_factory) == []

    live = await client.get("/api/v1/esp32/telemetry/latest", params={"system_id": str(system_id)})
    assert live.json()["packet"]["water_temp_c"] == 25.0

    assert await flush_esp32_interval(
        test_session_factory, system_id=system_id, now=T0 + timedelta(minutes=1),
    ) == "created"
    assert await flush_esp32_interval(
        test_session_factory, system_id=system_id, now=T0 + timedelta(minutes=1),
    ) == "not_due"

    rows = await stored(test_session_factory)
    assert len(rows) == 1
    assert rows[0].sequence == 2
    assert rows[0].received_at.replace(tzinfo=timezone.utc) == T0 + timedelta(seconds=58)

    config = await client.get("/api/v1/esp32/capture", params={"system_id": str(system_id)})
    assert config.json()["last_saved_scheduled_at"] is not None


@pytest.mark.asyncio
async def test_packet_at_boundary_does_not_replace_previous_window(client, test_session_factory):
    system_id = await make_system(client)
    await set_timed(test_session_factory, system_id)
    await accept(test_session_factory, system_id, 1, T0 + timedelta(seconds=59), 22)
    # Timer is deliberately late; incoming packet must close the old window first.
    await accept(test_session_factory, system_id, 2, T0 + timedelta(seconds=60), 29)
    rows = await stored(test_session_factory)
    assert len(rows) == 1
    assert rows[0].sequence == 1
    assert await flush_esp32_interval(
        test_session_factory, system_id=system_id, now=T0 + timedelta(seconds=60),
    ) == "not_due"


@pytest.mark.asyncio
async def test_disconnection_skips_stale_and_missing_intervals(client, test_session_factory):
    system_id = await make_system(client)
    await set_timed(test_session_factory, system_id)
    await accept(test_session_factory, system_id, 1, T0 + timedelta(seconds=5))
    assert await flush_esp32_interval(
        test_session_factory, system_id=system_id, now=T0 + timedelta(minutes=3),
    ) == "skipped"
    assert await stored(test_session_factory) == []
    # No stale packet is re-saved after the device reconnects.
    await accept(test_session_factory, system_id, 2, T0 + timedelta(minutes=3, seconds=58))
    assert await flush_esp32_interval(
        test_session_factory, system_id=system_id, now=T0 + timedelta(minutes=4),
    ) == "created"
    assert [r.sequence for r in await stored(test_session_factory)] == [2]


@pytest.mark.asyncio
async def test_admin_can_change_interval_and_restart_schedule(client, test_session_factory):
    system_id = await make_system(client)
    response = await client.put(
        "/api/v1/esp32/capture", params={"system_id": str(system_id)},
        json={"mode": "timed", "interval_minutes": 30},
    )
    assert response.status_code == 200
    assert response.json()["next_save_at"]
    before = response.json()["next_save_at"]
    fetched = await client.get("/api/v1/esp32/capture", params={"system_id": str(system_id)})
    assert fetched.json()["next_save_at"] == before
    bad = await client.put(
        "/api/v1/esp32/capture", params={"system_id": str(system_id)},
        json={"mode": "timed", "interval_minutes": 0},
    )
    assert bad.status_code == 422
    changed = await client.put(
        "/api/v1/esp32/capture", params={"system_id": str(system_id)},
        json={"mode": "live", "interval_minutes": 5},
    )
    assert changed.status_code == 200
    assert changed.json()["next_save_at"] is None
    assert (await client.get(
        "/api/v1/esp32/capture", params={"system_id": str(system_id)}
    )).json()["mode"] == "live"


@pytest.mark.asyncio
async def test_non_admin_cannot_change_capture_configuration(client, test_session_factory):
    from app.api.dependencies import get_current_user
    from app.db.enums import UserRole
    from app.main import app
    from app.models.system import User
    from uuid import uuid4

    system_id = await make_system(client)
    async def viewer():
        return User(
            id=uuid4(), username="viewer", password_hash="x",
            role=UserRole.VIEWER, is_active=True,
        )
    app.dependency_overrides[get_current_user] = viewer
    response = await client.put(
        "/api/v1/esp32/capture", params={"system_id": str(system_id)},
        json={"mode": "timed", "interval_minutes": 5},
    )
    assert response.status_code == 403
