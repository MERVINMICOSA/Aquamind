from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.models.feeding import FishPopulationRecord


pytestmark = pytest.mark.asyncio


async def create_tank(
    client: AsyncClient,
    *,
    suffix: str,
) -> UUID:
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": (
                f"Fish Population History System "
                f"{suffix}"
            ),
            "description": (
                "System for bounded fish population "
                "history testing."
            ),
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert system_response.status_code == 201

    system_id = system_response.json()["id"]

    tank_response = await client.post(
        "/api/v1/tanks",
        json={
            "system_id": system_id,
            "name": (
                f"Fish Population History Tank "
                f"{suffix}"
            ),
            "capacity_liters": 1000,
            "species": "Tilapia",
            "is_active": True,
        },
    )

    assert tank_response.status_code == 201

    return UUID(
        tank_response.json()["id"]
    )

async def test_population_history_is_bounded_and_newest_first(
    test_session,
    client: AsyncClient,
):
    tank_id = await create_tank(
        client,
        suffix="bounded",
    )

    base_time = datetime(
        2026,
        1,
        1,
        0,
        0,
        tzinfo=timezone.utc,
    )

    records = [
        FishPopulationRecord(
            tank_id=tank_id,
            species="Tilapia",
            count=index,
            estimated_biomass_grams=(
                1000.0 + index
            ),
            effective_at=(
                base_time
                + timedelta(minutes=index)
            ),
            recorded_by_user_id=None,
            notes=f"Population record {index}",
        )
        for index in range(51)
    ]

    test_session.add_all(records)
    await test_session.commit()

    response = await client.get(
        "/api/v1/feeding/population/history",
        params={
            "tank_id": tank_id,
        },
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 50

    assert history[0]["count"] == 50
    assert history[-1]["count"] == 1

    assert all(
        item["tank_id"] == str(tank_id)
        for item in history
    )


async def test_population_history_is_tank_scoped_and_paginated(
    test_session,
    client: AsyncClient,
):
    target_tank_id = await create_tank(
        client,
        suffix="target",
    )

    other_tank_id = await create_tank(
        client,
        suffix="other",
    )

    base_time = datetime(
        2026,
        2,
        1,
        0,
        0,
        tzinfo=timezone.utc,
    )

    target_records = [
        FishPopulationRecord(
            tank_id=target_tank_id,
            species="Tilapia",
            count=count,
            estimated_biomass_grams=(
                float(count * 100)
            ),
            effective_at=(
                base_time
                + timedelta(minutes=index)
            ),
            recorded_by_user_id=None,
            notes=None,
        )
        for index, count in enumerate(
            [10, 20, 30]
        )
    ]

    other_record = FishPopulationRecord(
        tank_id=other_tank_id,
        species="Tilapia",
        count=999,
        estimated_biomass_grams=99999.0,
        effective_at=(
            base_time
            + timedelta(hours=1)
        ),
        recorded_by_user_id=None,
        notes=None,
    )

    test_session.add_all(
        [
            *target_records,
            other_record,
        ]
    )

    await test_session.commit()

    response = await client.get(
        "/api/v1/feeding/population/history",
        params={
            "tank_id": target_tank_id,
            "limit": 2,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 2

    assert [
        item["count"]
        for item in history
    ] == [
        20,
        10,
    ]

    assert all(
        item["tank_id"] == str(target_tank_id)
        for item in history
    )

    assert all(
        item["count"] != 999
        for item in history
    )


async def test_population_history_rejects_limit_above_maximum(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/feeding/population/history",
        params={
            "tank_id": str(uuid4()),
            "limit": 101,
        },
    )

    assert response.status_code == 422


async def test_population_history_missing_tank_returns_404(
    client: AsyncClient,
):
    missing_tank_id = str(
        uuid4()
    )

    response = await client.get(
        "/api/v1/feeding/population/history",
        params={
            "tank_id": missing_tank_id,
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Tank not found",
    }


async def test_population_history_existing_tank_without_records_is_empty(
    client: AsyncClient,
):
    tank_id = await create_tank(
        client,
        suffix="empty",
    )

    response = await client.get(
        "/api/v1/feeding/population/history",
        params={
            "tank_id": tank_id,
        },
    )

    assert response.status_code == 200
    assert response.json() == []