import pytest


pytestmark = pytest.mark.asyncio


async def test_system_event_crud(client):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "System Event Test",
            "description": "System used for event API testing.",
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert system_response.status_code == 201

    system = system_response.json()

    create_response = await client.post(
        "/api/v1/system-events",
        json={
            "system_id": system["id"],
            "event_type": "pump_started",
            "severity": "info",
            "message": "Main circulation pump started.",
            "event_metadata": {
                "source": "test",
            },
            "occurred_at": "2026-01-01T12:00:00Z",
        },
    )

    assert create_response.status_code == 201

    event = create_response.json()

    assert event["system_id"] == system["id"]
    assert event["event_type"] == "pump_started"
    assert event["severity"] == "info"
    assert event["message"] == "Main circulation pump started."
    assert event["event_metadata"] == {
        "source": "test",
    }

    event_id = event["id"]

    get_response = await client.get(
        f"/api/v1/system-events/{event_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == event_id

    list_response = await client.get(
        "/api/v1/system-events",
        params={
            "system_id": system["id"],
            "severity": "info",
            "event_type": "pump_started",
        },
    )

    assert list_response.status_code == 200

    events = list_response.json()

    assert len(events) == 1
    assert events[0]["id"] == event_id

    update_response = await client.patch(
        f"/api/v1/system-events/{event_id}",
        json={
            "severity": "warning",
            "message": "Pump runtime exceeded expected duration.",
            "event_metadata": {
                "source": "test",
                "runtime_seconds": 420,
            },
        },
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["severity"] == "warning"
    assert (
        updated["message"]
        == "Pump runtime exceeded expected duration."
    )
    assert (
        updated["event_metadata"]["runtime_seconds"]
        == 420
    )

    delete_response = await client.delete(
        f"/api/v1/system-events/{event_id}"
    )

    assert delete_response.status_code == 204

    missing_response = await client.get(
        f"/api/v1/system-events/{event_id}"
    )

    assert missing_response.status_code == 404
    assert (
        missing_response.json()["detail"]
        == "System event not found"
    )


async def test_system_event_requires_existing_system(client):
    response = await client.post(
        "/api/v1/system-events",
        json={
            "system_id": (
                "00000000-0000-0000-0000-000000000000"
            ),
            "event_type": "invalid_test_event",
            "severity": "error",
            "message": "This should not be created.",
            "event_metadata": None,
            "occurred_at": "2026-01-01T12:00:00Z",
        },
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Aquaponics system not found"
    )


async def test_system_event_not_found(client):
    response = await client.get(
        "/api/v1/system-events/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "System event not found"
    )