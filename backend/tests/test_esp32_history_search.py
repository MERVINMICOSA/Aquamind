"""Server-side history search over PostgreSQL-compatible archived packet JSON."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.models.esp32_telemetry import Esp32Telemetry
from app.models.system import AquaponicsSystem

pytestmark = pytest.mark.asyncio


async def populate_history(session):
    system = AquaponicsSystem(name="Searchable archive test", timezone="UTC")
    other = AquaponicsSystem(name="Separate system", timezone="UTC")
    session.add_all([system, other])
    await session.flush()

    base = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    for i in range(5):
        session.add(Esp32Telemetry(
            system_id=system.id,
            device_id="esp32-devkit-01",
            sequence=i,
            uptime_ms=i * 1000,
            received_at=base + timedelta(days=i),
            packet={
                "type": "aquamind_sensor",
                "schema_version": 1,
                "device_id": "esp32-devkit-01",
                "sequence": i,
                "uptime_ms": i * 1000,
                "water_temp_c": 25.0 + i if i != 2 else None,
                "ph_calibrated": False,
                "ph": None,
                "tds_calibrated": False,
                "tds_ppm": None,
                "humidity_pct": 80.0 - i,
            },
        ))
    session.add(Esp32Telemetry(
        system_id=other.id,
        device_id="esp32-devkit-01",
        sequence=200,
        uptime_ms=200000,
        received_at=base + timedelta(days=5),
        packet={
            "type": "aquamind_sensor",
            "schema_version": 1,
            "device_id": "esp32-devkit-01",
            "sequence": 200, "uptime_ms": 200000,
            "water_temp_c": 88.0,
            "ph_calibrated": False, "ph": None,
            "tds_calibrated": False, "tds_ppm": None,
        },
    ))
    await session.commit()
    return system.id, other.id


async def test_search_filters_numeric_values_server_side_and_pages(client, test_session):
    system_id, _ = await populate_history(test_session)
    url = "/api/v1/esp32/telemetry/search"

    response = await client.get(url, params={
        "system_id": str(system_id), "field": "water_temp_c",
        "limit": 2, "offset": 0,
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 4
    assert data["limit"] == 2
    assert [x["packet"]["water_temp_c"] for x in data["items"]] == [29.0, 28.0]

    next_page = await client.get(url, params={
        "system_id": str(system_id), "field": "water_temp_c",
        "limit": 2, "offset": 2,
    })
    assert next_page.status_code == 200, next_page.text
    assert next_page.json()["total"] == 4
    assert [x["packet"]["water_temp_c"] for x in next_page.json()["items"]] == [26.0, 25.0]


async def test_search_date_bounds_and_value_bounds_apply_before_pagination(
    client, test_session,
):
    system_id, _ = await populate_history(test_session)
    url = "/api/v1/esp32/telemetry/search"
    response = await client.get(url, params={
        "system_id": str(system_id), "field": "humidity_pct",
        "start_at": "2026-11-02T00:00:00+08:00",
        "end_at": "2026-11-05T00:00:00+08:00",
        "min_value": 78, "max_value": 79,
    })
    assert response.status_code == 200, response.text
    values = [x["packet"]["humidity_pct"] for x in response.json()["items"]]
    assert values == [78.0, 79.0]
    assert response.json()["total"] == 2


async def test_search_rejects_invalid_filters(client, test_session):
    system_id, _ = await populate_history(test_session)
    url = "/api/v1/esp32/telemetry/search"
    cases = [
        {"field": "ph_unverified_estimate"},
        {"field": "arbitrary_sql_column"},
        {"field": "water_temp_c", "limit": 101},
        {"field": "water_temp_c", "offset": -1},
        {"field": "water_temp_c", "min_value": 10, "max_value": 9},
        {"field": "water_temp_c", "start_at": "2026-11-01T00:00:00"},
        {"field": "water_temp_c", "end_at": "2026-11-01T00:00:00"},
        {"field": "water_temp_c", "start_at": "2026-11-05T00:00:00Z",
         "end_at": "2026-11-04T00:00:00Z"},
    ]
    for invalid in cases:
        response = await client.get(url, params={"system_id": str(system_id), **invalid})
        assert response.status_code == 422, (invalid, response.text)


async def test_search_restricts_system_and_does_not_modify_archive(client, test_session):
    system_id, other_id = await populate_history(test_session)
    response = await client.get("/api/v1/esp32/telemetry/search", params={
        "system_id": str(other_id),
        "field": "water_temp_c",
    })
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["packet"]["water_temp_c"] == 88.0
    assert (await test_session.execute(select(Esp32Telemetry))).scalars().all().__len__() == 6

    empty = await client.get("/api/v1/esp32/telemetry/search", params={
        "system_id": str(uuid4()),
        "field": "water_temp_c",
    })
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
    assert empty.json()["items"] == []
