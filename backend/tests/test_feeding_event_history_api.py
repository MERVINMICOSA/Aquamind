from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


async def _create_system(
    client: AsyncClient,
    *,
    name: str,
) -> str:
    response = await client.post(
        "/api/v1/systems",
        json={
            "name": name,
            "description": None,
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


async def _create_tank(
    client: AsyncClient,
    *,
    system_id: str,
    name: str,
) -> str:
    response = await client.post(
        "/api/v1/tanks",
        json={
            "system_id": system_id,
            "name": name,
            "capacity_liters": 1000,
            "species": "Tilapia",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


async def _create_feeder(
    client: AsyncClient,
    *,
    system_id: str,
    tank_id: str,
    suffix: str,
) -> str:
    response = await client.post(
        "/api/v1/actuators",
        json={
            "system_id": system_id,
            "name": f"History Feeder {suffix}",
            "actuator_type": "fish_feeder",
            "control_mode": "scheduled",
            "hardware_identifier": (
                f"FEED-HISTORY-{suffix}"
            ),
            "location_type": "tank",
            "location_id": tank_id,
            "is_enabled": True,
            "safety_config": None,
            "current_state": "off",
            "current_value": None,
            "last_state_at": None,
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


async def _create_feeding_event(
    client: AsyncClient,
    *,
    actuator_id: str,
    tank_id: str,
    executed_at: datetime,
    amount_grams: float,
) -> dict:
    actuator_response = await client.post(
        "/api/v1/actuator-events",
        json={
            "actuator_id": actuator_id,
            "command_type": "activate",
            "requested_value": 1,
            "actual_value": 1,
            "started_at": executed_at.isoformat(),
            "completed_at": (
                executed_at
                + timedelta(seconds=1)
            ).isoformat(),
            "duration_ms": 1000,
            "trigger_source": "schedule",
            "status": "completed",
            "fault_code": None,
            "error_message": None,
        },
    )

    assert actuator_response.status_code == 201

    actuator_event_id = (
        actuator_response.json()["id"]
    )

    feeding_response = await client.post(
        "/api/v1/feeding/events",
        json={
            "schedule_id": None,
            "actuator_event_id": (
                actuator_event_id
            ),
            "tank_id": tank_id,
            "amount_grams": amount_grams,
            "duration_seconds": 1,
            "calculated_from_biomass": None,
            "calibration_id": None,
            "executed_at": (
                executed_at.isoformat()
            ),
            "status": "completed",
            "notes": None,
        },
    )

    assert feeding_response.status_code == 201

    return feeding_response.json()


@pytest.mark.asyncio
async def test_feeding_event_history_is_bounded_and_newest_first(
    client: AsyncClient,
):
    system_id = await _create_system(
        client,
        name="Feeding History Bounded System",
    )

    tank_id = await _create_tank(
        client,
        system_id=system_id,
        name="Feeding History Tank",
    )

    actuator_id = await _create_feeder(
        client,
        system_id=system_id,
        tank_id=tank_id,
        suffix="BOUND",
    )

    base_time = datetime(
        2026,
        1,
        1,
        8,
        0,
        tzinfo=timezone.utc,
    )

    created_ids: list[str] = []

    for index in range(51):
        event = await _create_feeding_event(
            client,
            actuator_id=actuator_id,
            tank_id=tank_id,
            executed_at=(
                base_time
                + timedelta(minutes=index)
            ),
            amount_grams=float(index + 1),
        )

        created_ids.append(
            event["id"]
        )

    history_response = await client.get(
        "/api/v1/feeding/events/history",
        params={
            "system_id": system_id,
        },
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert len(history) == 50

    assert [
        event["id"]
        for event in history
    ] == list(
        reversed(
            created_ids[1:]
        )
    )

    generic_response = await client.get(
        "/api/v1/feeding/events",
        params={
            "tank_id": tank_id,
        },
    )

    assert generic_response.status_code == 200
    assert len(generic_response.json()) == 51


@pytest.mark.asyncio
async def test_feeding_event_history_is_system_scoped_and_paginated(
    client: AsyncClient,
):
    system_one_id = await _create_system(
        client,
        name="Feeding History System One",
    )

    system_two_id = await _create_system(
        client,
        name="Feeding History System Two",
    )

    tank_one_id = await _create_tank(
        client,
        system_id=system_one_id,
        name="System One Tank",
    )

    tank_two_id = await _create_tank(
        client,
        system_id=system_two_id,
        name="System Two Tank",
    )

    actuator_one_id = await _create_feeder(
        client,
        system_id=system_one_id,
        tank_id=tank_one_id,
        suffix="SYS1",
    )

    actuator_two_id = await _create_feeder(
        client,
        system_id=system_two_id,
        tank_id=tank_two_id,
        suffix="SYS2",
    )

    base_time = datetime(
        2026,
        2,
        1,
        8,
        0,
        tzinfo=timezone.utc,
    )

    system_one_events = []

    for index in range(3):
        event = await _create_feeding_event(
            client,
            actuator_id=actuator_one_id,
            tank_id=tank_one_id,
            executed_at=(
                base_time
                + timedelta(minutes=index)
            ),
            amount_grams=float(index + 1),
        )

        system_one_events.append(
            event
        )

        await _create_feeding_event(
            client,
            actuator_id=actuator_two_id,
            tank_id=tank_two_id,
            executed_at=(
                base_time
                + timedelta(
                    minutes=index,
                    seconds=30,
                )
            ),
            amount_grams=float(index + 10),
        )

    response = await client.get(
        "/api/v1/feeding/events/history",
        params={
            "system_id": system_one_id,
            "limit": 2,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    first_page = response.json()

    assert [
        event["id"]
        for event in first_page
    ] == [
        system_one_events[2]["id"],
        system_one_events[1]["id"],
    ]

    assert all(
        event["tank_id"] == tank_one_id
        for event in first_page
    )

    response = await client.get(
        "/api/v1/feeding/events/history",
        params={
            "system_id": system_one_id,
            "limit": 2,
            "offset": 2,
        },
    )

    assert response.status_code == 200

    second_page = response.json()

    assert [
        event["id"]
        for event in second_page
    ] == [
        system_one_events[0]["id"],
    ]


@pytest.mark.asyncio
async def test_feeding_event_history_rejects_limit_above_100(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/feeding/events/history",
        params={
            "system_id": (
                "00000000-0000-0000-"
                "0000-000000000001"
            ),
            "limit": 101,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_feeding_event_history_requires_existing_system(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/feeding/events/history",
        params={
            "system_id": (
                "00000000-0000-0000-"
                "0000-000000000000"
            ),
        },
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Aquaponics system not found"
    )


@pytest.mark.asyncio
async def test_feeding_event_history_returns_empty_for_system_without_events(
    client: AsyncClient,
):
    system_id = await _create_system(
        client,
        name="Empty Feeding History System",
    )

    response = await client.get(
        "/api/v1/feeding/events/history",
        params={
            "system_id": system_id,
        },
    )

    assert response.status_code == 200
    assert response.json() == []