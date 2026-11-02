from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from uuid import UUID

import pytest

from app.db.enums import (
    ExecutionStatus,
    RefillTrigger,
)
from app.models.refill import (
    RefillEvent,
)
from app.models.system import (
    AquaponicsSystem,
    Reservoir,
    Tank,
)


pytestmark = pytest.mark.asyncio


HISTORY_COUNT = 105


async def create_history_data(
    test_session,
):
    system = AquaponicsSystem(
        name="Refill History System",
        description=(
            "System for bounded refill "
            "history API tests."
        ),
        timezone="UTC",
        is_active=True,
    )

    test_session.add(
        system
    )

    await test_session.flush()

    reservoir = Reservoir(
        system_id=system.id,
        name="History Reservoir",
        capacity_liters=1000,
        is_active=True,
    )

    other_reservoir = Reservoir(
        system_id=system.id,
        name="Other History Reservoir",
        capacity_liters=1000,
        is_active=True,
    )

    tank = Tank(
        system_id=system.id,
        name="History Tank",
        capacity_liters=500,
        species="Synthetic Test Species",
        is_active=True,
    )

    test_session.add_all(
        [
            reservoir,
            other_reservoir,
            tank,
        ]
    )

    await test_session.flush()

    base_started_at = datetime(
        2026,
        1,
        10,
        12,
        0,
        tzinfo=timezone.utc,
    )

    expected_rows: list[
        tuple[
            datetime,
            UUID,
        ]
    ] = []

    events: list[
        RefillEvent
    ] = []

    for index in range(
        HISTORY_COUNT
    ):
        
         #Repeated timestamps intentionally exercise
         #the deterministic UUID tie-break.
         
        started_at = (
            base_started_at
            - timedelta(
                minutes=index // 3
            )
        )

        event_id = UUID(
            int=1000 + index
        )

        event = RefillEvent(
            id=event_id,
            reservoir_id=reservoir.id,
            target_tank_id=tank.id,
            start_level_percent=20.0,
            end_level_percent=80.0,
            started_at=started_at,
            completed_at=(
                started_at
                + timedelta(
                    minutes=5
                )
            ),
            duration_seconds=300.0,
            trigger=RefillTrigger.AUTOMATIC,
            status=ExecutionStatus.COMPLETED,
            timeout_reason=None,
        )

        events.append(
            event
        )

        expected_rows.append(
            (
                started_at,
                event_id,
            )
        )

   
     #This event is newer than every event above.
     #It must never consume a page slot for the
     #requested reservoir.
     
    other_event = RefillEvent(
        id=UUID(
            int=999999
        ),
        reservoir_id=other_reservoir.id,
        target_tank_id=tank.id,
        start_level_percent=25.0,
        end_level_percent=75.0,
        started_at=(
            base_started_at
            + timedelta(
                days=1
            )
        ),
        completed_at=(
            base_started_at
            + timedelta(
                days=1,
                minutes=5,
            )
        ),
        duration_seconds=300.0,
        trigger=RefillTrigger.AUTOMATIC,
        status=ExecutionStatus.COMPLETED,
        timeout_reason=None,
    )

    test_session.add_all(
        [
            *events,
            other_event,
        ]
    )

    await test_session.commit()

    expected_ids = [
        str(event_id)
        for (
            _,
            event_id,
        )
        in sorted(
            expected_rows,
            key=lambda item: (
                item[0],
                item[1].int,
            ),
            reverse=True,
        )
    ]

    return {
        "system": system,
        "reservoir": reservoir,
        "other_reservoir": (
            other_reservoir
        ),
        "tank": tank,
        "expected_ids": expected_ids,
    }


async def test_refill_history_default_page_and_contract(
    client,
    test_session,
):
    data = await create_history_data(
        test_session
    )

    response = await client.get(
        "/api/v1/refill-events/history",
        params={
            "reservoir_id": (
                str(
                    data[
                        "reservoir"
                    ].id
                )
            ),
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert len(payload) == 50

    assert [
        item["id"]
        for item in payload
    ] == data["expected_ids"][:50]

    assert all(
        item["reservoir_id"]
        == str(
            data["reservoir"].id
        )
        for item in payload
    )

    assert set(
        payload[0].keys()
    ) == {
        "id",
        "reservoir_id",
        "target_tank_id",
        "start_level_percent",
        "end_level_percent",
        "started_at",
        "completed_at",
        "duration_seconds",
        "trigger",
        "status",
        "timeout_reason",
        "created_at",
    }


async def test_generic_refill_list_remains_unbounded(
    client,
    test_session,
):
    data = await create_history_data(
        test_session
    )

    response = await client.get(
        "/api/v1/refill-events",
        params={
            "reservoir_id": str(
                data["reservoir"].id
            ),
        },
    )

    assert response.status_code == 200

    assert len(
        response.json()
    ) == HISTORY_COUNT


@pytest.mark.parametrize(
    (
        "limit",
        "expected_count",
    ),
    [
        (1, 1),
        (51, 51),
        (100, 100),
    ],
)
async def test_refill_history_respects_limit(
    client,
    test_session,
    limit,
    expected_count,
):
    data = await create_history_data(
        test_session
    )

    response = await client.get(
        "/api/v1/refill-events/history",
        params={
            "reservoir_id": str(
                data["reservoir"].id
            ),
            "limit": limit,
        },
    )

    assert response.status_code == 200

    assert len(
        response.json()
    ) == expected_count


async def test_refill_history_respects_offset(
    client,
    test_session,
):
    data = await create_history_data(
        test_session
    )

    response = await client.get(
        "/api/v1/refill-events/history",
        params={
            "reservoir_id": str(
                data["reservoir"].id
            ),
            "limit": 50,
            "offset": 50,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert len(payload) == 50

    assert [
        item["id"]
        for item in payload
    ] == data["expected_ids"][
        50:100
    ]


@pytest.mark.parametrize(
    (
        "params",
    ),
    [
        (
            {
                "reservoir_id": (
                    "not-a-uuid"
                ),
            },
        ),
        (
            {
                "reservoir_id": (
                    "00000000-0000-0000-"
                    "0000-000000000001"
                ),
                "limit": 0,
            },
        ),
        (
            {
                "reservoir_id": (
                    "00000000-0000-0000-"
                    "0000-000000000001"
                ),
                "limit": 101,
            },
        ),
        (
            {
                "reservoir_id": (
                    "00000000-0000-0000-"
                    "0000-000000000001"
                ),
                "offset": -1,
            },
        ),
    ],
)
async def test_refill_history_rejects_invalid_query_values(
    client,
    params,
):
    response = await client.get(
        "/api/v1/refill-events/history",
        params=params,
    )

    assert response.status_code == 422


async def test_refill_history_requires_reservoir_id(
    client,
):
    response = await client.get(
        "/api/v1/refill-events/history"
    )

    assert response.status_code == 422


async def test_refill_history_missing_reservoir_returns_404(
    client,
):
    response = await client.get(
        "/api/v1/refill-events/history",
        params={
            "reservoir_id": (
                "00000000-0000-0000-"
                "0000-000000000000"
            ),
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": (
            "Reservoir not found"
        )
    }


async def test_refill_history_soft_deleted_reservoir_returns_404(
    client,
    test_session,
):
    system = AquaponicsSystem(
        name="Deleted Refill History System",
        description=None,
        timezone="UTC",
        is_active=True,
    )

    test_session.add(
        system
    )

    await test_session.flush()

    reservoir = Reservoir(
        system_id=system.id,
        name="Deleted History Reservoir",
        capacity_liters=1000,
        is_active=True,
        deleted_at=datetime.now(
            timezone.utc
        ),
    )

    test_session.add(
        reservoir
    )

    await test_session.commit()

    response = await client.get(
        "/api/v1/refill-events/history",
        params={
            "reservoir_id": str(
                reservoir.id
            ),
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": (
            "Reservoir not found"
        )
    }


async def test_refill_history_empty_reservoir_returns_empty_list(
    client,
    test_session,
):
    system = AquaponicsSystem(
        name="Empty Refill History System",
        description=None,
        timezone="UTC",
        is_active=True,
    )

    test_session.add(
        system
    )

    await test_session.flush()

    reservoir = Reservoir(
        system_id=system.id,
        name="Empty History Reservoir",
        capacity_liters=1000,
        is_active=True,
    )

    test_session.add(
        reservoir
    )

    await test_session.commit()

    response = await client.get(
        "/api/v1/refill-events/history",
        params={
            "reservoir_id": str(
                reservoir.id
            ),
        },
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_refill_history_exhausted_page_returns_empty_list(
    client,
    test_session,
):
    data = await create_history_data(
        test_session
    )

    response = await client.get(
        "/api/v1/refill-events/history",
        params={
            "reservoir_id": str(
                data["reservoir"].id
            ),
            "offset": HISTORY_COUNT,
        },
    )

    assert response.status_code == 200
    assert response.json() == []