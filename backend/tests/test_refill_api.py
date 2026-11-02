import pytest

pytestmark = pytest.mark.asyncio

from datetime import datetime, timezone


async def test_refill_event_crud(client):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Test Refill System",
            "description": "System created for refill event API testing.",
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert system_response.status_code == 201
    system = system_response.json()

    reservoir_response = await client.post(
        "/api/v1/reservoirs",
        json={
            "system_id": system["id"],
            "name": "Test Refill Reservoir",
            "capacity_liters": 1000,
            "is_active": True,
        },
    )

    assert reservoir_response.status_code == 201
    reservoir = reservoir_response.json()

    tank_response = await client.post(
        "/api/v1/tanks",
        json={
            "system_id": system["id"],
            "name": "Test Refill Tank",
            "capacity_liters": 500,
            "species": "Tilapia",
            "is_active": True,
        },
    )

    assert tank_response.status_code == 201
    tank = tank_response.json()

    create_response = await client.post(
        "/api/v1/refill-events",
        json={
            "reservoir_id": reservoir["id"],
            "target_tank_id": tank["id"],
            "start_level_percent": 20.0,
            "end_level_percent": 80.0,
            "started_at": "2026-01-01T10:00:00Z",
            "completed_at": "2026-01-01T10:05:00Z",
            "duration_seconds": 300,
            "trigger": "manual",
            "status": "completed",
            "timeout_reason": None,
        },
    )

    print(
        "REFILL EVENT CREATE RESPONSE:",
        create_response.status_code,
        create_response.json(),
    )

    assert create_response.status_code == 201

    event = create_response.json()

    assert event["reservoir_id"] == reservoir["id"]
    assert event["target_tank_id"] == tank["id"]
    assert event["start_level_percent"] == 20.0
    assert event["end_level_percent"] == 80.0
    assert event["duration_seconds"] == 300.0
    assert event["trigger"] == "manual"
    assert event["status"] == "completed"

    get_response = await client.get(
        f"/api/v1/refill-events/{event['id']}"
    )

    print(
        "REFILL EVENT GET RESPONSE:",
        get_response.status_code,
        get_response.json(),
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == event["id"]

    update_response = await client.patch(
        f"/api/v1/refill-events/{event['id']}",
        json={
            "end_level_percent": 90.0,
            "duration_seconds": 360,
            "status": "completed",
        },
    )

    print(
        "REFILL EVENT UPDATE RESPONSE:",
        update_response.status_code,
        update_response.json(),
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["end_level_percent"] == 90.0
    assert updated["duration_seconds"] == 360.0

    list_response = await client.get(
        "/api/v1/refill-events",
        params={
            "reservoir_id": reservoir["id"],
        },
    )

    print(
        "REFILL EVENT LIST RESPONSE:",
        list_response.status_code,
        list_response.json(),
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    delete_response = await client.delete(
        f"/api/v1/refill-events/{event['id']}"
    )

    print(
        "REFILL EVENT DELETE RESPONSE:",
        delete_response.status_code,
    )

    assert delete_response.status_code == 204

    missing_response = await client.get(
        f"/api/v1/refill-events/{event['id']}"
    )

    print(
        "REFILL EVENT AFTER DELETE RESPONSE:",
        missing_response.status_code,
        missing_response.json(),
    )

    assert missing_response.status_code == 404


async def test_refill_event_rejects_cross_system_reservoir_and_tank(client):
    system_one_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Refill System One",
            "description": "First refill validation system.",
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert system_one_response.status_code == 201
    system_one = system_one_response.json()

    system_two_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Refill System Two",
            "description": "Second refill validation system.",
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert system_two_response.status_code == 201
    system_two = system_two_response.json()

    reservoir_response = await client.post(
        "/api/v1/reservoirs",
        json={
            "system_id": system_one["id"],
            "name": "System One Reservoir",
            "capacity_liters": 1000,
            "is_active": True,
        },
    )

    assert reservoir_response.status_code == 201
    reservoir = reservoir_response.json()

    tank_response = await client.post(
        "/api/v1/tanks",
        json={
            "system_id": system_two["id"],
            "name": "System Two Tank",
            "capacity_liters": 500,
            "species": "Tilapia",
            "is_active": True,
        },
    )

    assert tank_response.status_code == 201
    tank = tank_response.json()

    response = await client.post(
        "/api/v1/refill-events",
        json={
            "reservoir_id": reservoir["id"],
            "target_tank_id": tank["id"],
            "start_level_percent": 20.0,
            "end_level_percent": 80.0,
            "started_at": "2026-01-01T10:00:00Z",
            "completed_at": "2026-01-01T10:05:00Z",
            "duration_seconds": 300,
            "trigger": "manual",
            "status": "completed",
        },
    )

    print(
        "CROSS-SYSTEM REFILL RESPONSE:",
        response.status_code,
        response.json(),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Reservoir and target tank must belong to the same system"
    )


async def test_refill_event_not_found(client):
    response = await client.get(
        "/api/v1/refill-events/"
        "00000000-0000-0000-0000-000000000000"
    )

    print(
        "INVALID REFILL EVENT RESPONSE:",
        response.status_code,
        response.json(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Refill event not found"