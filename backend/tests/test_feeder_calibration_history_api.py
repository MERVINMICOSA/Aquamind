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


async def _create_actuator(
    client: AsyncClient,
    *,
    system_id: str,
    suffix: str,
) -> str:
    response = await client.post(
        "/api/v1/actuators",
        json={
            "system_id": system_id,
            "name": (
                f"Calibration History Feeder {suffix}"
            ),
            "actuator_type": "fish_feeder",
            "control_mode": "scheduled",
            "hardware_identifier": None,
            "location_type": None,
            "location_id": None,
            "is_enabled": False,
            "safety_config": None,
            "current_state": "off",
            "current_value": None,
            "last_state_at": None,
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


async def _create_calibration(
    client: AsyncClient,
    *,
    actuator_id: str,
    performed_at: datetime,
    run_count: int,
) -> dict:
    measured_seconds = 10.0
    measured_grams = float(
        run_count * 10
    )

    response = await client.post(
        "/api/v1/feeding/calibrations",
        json={
            "actuator_id": actuator_id,
            "run_count": run_count,
            "measured_seconds": (
                measured_seconds
            ),
            "measured_grams": (
                measured_grams
            ),
            "grams_per_second": (
                measured_grams
                / measured_seconds
            ),
            "calibration_method": (
                "measured_average"
            ),
            "performed_at": (
                performed_at.isoformat()
            ),
            "verified_by_user_id": None,
            "notes": None,
        },
    )

    assert response.status_code == 201

    return response.json()


@pytest.mark.asyncio
async def test_feeder_calibration_history_is_bounded_and_newest_first(
    client: AsyncClient,
):
    system_id = await _create_system(
        client,
        name=(
            "Calibration History Bounded System"
        ),
    )

    actuator_id = await _create_actuator(
        client,
        system_id=system_id,
        suffix="BOUND",
    )

    base_time = datetime(
        2026,
        3,
        1,
        8,
        0,
        tzinfo=timezone.utc,
    )

    created_ids: list[str] = []

    for index in range(51):
        calibration = await _create_calibration(
            client,
            actuator_id=actuator_id,
            performed_at=(
                base_time
                + timedelta(minutes=index)
            ),
            run_count=index + 1,
        )

        created_ids.append(
            calibration["id"]
        )

    response = await client.get(
        "/api/v1/feeding/calibrations/history",
        params={
            "actuator_id": actuator_id,
        },
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 50

    assert [
        item["id"]
        for item in history
    ] == list(
        reversed(
            created_ids[1:]
        )
    )

    generic_response = await client.get(
        "/api/v1/feeding/calibrations",
        params={
            "actuator_id": actuator_id,
        },
    )

    assert generic_response.status_code == 200
    assert len(generic_response.json()) == 51


@pytest.mark.asyncio
async def test_feeder_calibration_history_is_actuator_scoped_and_paginated(
    client: AsyncClient,
):
    system_id = await _create_system(
        client,
        name=(
            "Calibration History Scoped System"
        ),
    )

    actuator_one_id = await _create_actuator(
        client,
        system_id=system_id,
        suffix="ONE",
    )

    actuator_two_id = await _create_actuator(
        client,
        system_id=system_id,
        suffix="TWO",
    )

    base_time = datetime(
        2026,
        4,
        1,
        8,
        0,
        tzinfo=timezone.utc,
    )

    actuator_one_calibrations = []

    for index in range(3):
        calibration = await _create_calibration(
            client,
            actuator_id=actuator_one_id,
            performed_at=(
                base_time
                + timedelta(minutes=index)
            ),
            run_count=index + 1,
        )

        actuator_one_calibrations.append(
            calibration
        )

        await _create_calibration(
            client,
            actuator_id=actuator_two_id,
            performed_at=(
                base_time
                + timedelta(
                    minutes=index,
                    seconds=30,
                )
            ),
            run_count=index + 10,
        )

    response = await client.get(
        "/api/v1/feeding/calibrations/history",
        params={
            "actuator_id":
                actuator_one_id,
            "limit": 2,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    first_page = response.json()

    assert [
        item["id"]
        for item in first_page
    ] == [
        actuator_one_calibrations[2]["id"],
        actuator_one_calibrations[1]["id"],
    ]

    assert all(
        item["actuator_id"]
        == actuator_one_id
        for item in first_page
    )

    response = await client.get(
        "/api/v1/feeding/calibrations/history",
        params={
            "actuator_id":
                actuator_one_id,
            "limit": 2,
            "offset": 2,
        },
    )

    assert response.status_code == 200

    second_page = response.json()

    assert [
        item["id"]
        for item in second_page
    ] == [
        actuator_one_calibrations[0]["id"],
    ]


@pytest.mark.asyncio
async def test_feeder_calibration_history_rejects_limit_above_100(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/feeding/calibrations/history",
        params={
            "actuator_id": (
                "00000000-0000-0000-"
                "0000-000000000001"
            ),
            "limit": 101,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_feeder_calibration_history_requires_existing_actuator(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/feeding/calibrations/history",
        params={
            "actuator_id": (
                "00000000-0000-0000-"
                "0000-000000000000"
            ),
        },
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Actuator not found"
    )


@pytest.mark.asyncio
async def test_feeder_calibration_history_returns_empty_for_actuator_without_calibrations(
    client: AsyncClient,
):
    system_id = await _create_system(
        client,
        name=(
            "Empty Calibration History System"
        ),
    )

    actuator_id = await _create_actuator(
        client,
        system_id=system_id,
        suffix="EMPTY",
    )

    response = await client.get(
        "/api/v1/feeding/calibrations/history",
        params={
            "actuator_id": actuator_id,
        },
    )

    assert response.status_code == 200
    assert response.json() == []