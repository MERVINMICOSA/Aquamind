from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from app.models.actuators import Actuator, ActuatorEvent
from app.models.system import AquaponicsSystem


HISTORY_URL = "/api/v1/actuator-events/history"


@pytest_asyncio.fixture
async def history_data(test_session):
    system = AquaponicsSystem(name="Event history test", timezone="UTC")
    actuators = [
        Actuator(
            system=system,
            name=f"History actuator {index}",
            actuator_type="water_pump",
            control_mode="manual",
            is_enabled=index != 0,
        )
        for index in range(3)
    ]
    test_session.add_all(actuators)
    await test_session.flush()

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    for index in range(105):
        event = ActuatorEvent(
            id=UUID(int=index + 1),
            actuator_id=actuators[0].id,
            command_type="activate",
            started_at=base + timedelta(minutes=index // 4),
            created_at=base - timedelta(seconds=index // 2),
            trigger_source="manual",
            status="pending",
        )
        events.append(event)
        test_session.add(event)
    # A newer event from another actuator must not consume a page slot.
    test_session.add(ActuatorEvent(
        actuator_id=actuators[1].id,
        command_type="deactivate",
        started_at=base + timedelta(days=1),
        created_at=base + timedelta(days=1),
        trigger_source="system",
        status="completed",
    ))
    await test_session.commit()
    ordered = sorted(
        events,
        key=lambda event: (event.started_at, event.created_at, event.id),
        reverse=True,
    )
    return actuators, [str(event.id) for event in ordered]


@pytest.mark.asyncio
async def test_history_defaults_contract_and_generic_list_unchanged(client, history_data):
    actuators, expected = history_data
    params = {"actuator_id": str(actuators[0].id)}
    response = await client.get(HISTORY_URL, params=params)
    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == expected[:50]
    assert set(rows[0]) == {
        "id", "actuator_id", "command_type", "requested_value", "actual_value",
        "started_at", "completed_at", "duration_ms", "trigger_source", "status",
        "fault_code", "error_message", "created_at",
    }
    assert rows[0]["status"] == "pending"
    for field in ("requested_value", "actual_value", "completed_at", "duration_ms",
                  "fault_code", "error_message"):
        assert rows[0][field] is None

    generic = await client.get("/api/v1/actuator-events", params=params)
    assert generic.status_code == 200
    assert len(generic.json()) == 105
    assert {row["id"] for row in generic.json()} == set(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 51, 100])
async def test_history_filter_order_and_pagination(client, history_data, limit):
    actuators, expected = history_data
    pages = []
    for offset in (0, limit):
        response = await client.get(HISTORY_URL, params={
            "actuator_id": str(actuators[0].id), "limit": limit, "offset": offset,
        })
        assert response.status_code == 200
        rows = response.json()
        assert all(row["actuator_id"] == str(actuators[0].id) for row in rows)
        ids = [row["id"] for row in rows]
        assert ids == expected[offset:offset + limit]
        pages.append(ids)
    assert set(pages[0]).isdisjoint(pages[1])


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [
    {},
    {"actuator_id": "invalid"},
    *[{"actuator_id": str(UUID(int=1)), "limit": value}
      for value in (0, -1, 101, "invalid", "1.5")],
    *[{"actuator_id": str(UUID(int=1)), "offset": value}
      for value in (-1, "invalid", "1.5")],
])
async def test_history_invalid_queries(client, params):
    response = await client.get(HISTORY_URL, params=params)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_history_missing_and_soft_deleted_actuator(client, history_data, test_session):
    actuators, _ = history_data
    actuators[0].deleted_at = datetime.now(timezone.utc)
    await test_session.commit()
    for actuator_id in (uuid4(), actuators[0].id):
        response = await client.get(HISTORY_URL, params={"actuator_id": str(actuator_id)})
        assert response.status_code == 404
        assert response.json() == {"detail": "Actuator not found"}


@pytest.mark.asyncio
async def test_history_empty_and_exhausted_page(client, history_data):
    actuators, _ = history_data
    for actuator_id, offset in ((actuators[2].id, 0), (actuators[0].id, 105)):
        response = await client.get(HISTORY_URL, params={
            "actuator_id": str(actuator_id), "offset": offset,
        })
        assert response.status_code == 200
        assert response.json() == []
