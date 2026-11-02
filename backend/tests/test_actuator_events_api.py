import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_actuator_event_create_get_update_list_and_filter(
    client: AsyncClient,
):
    """
    Integration test for the actuator event lifecycle.

    Creates:
    1. A parent aquaponics system
    2. An actuator belonging to that system
    3. An actuator event belonging to that actuator

    Then:
    - Creates the actuator event
    - Retrieves the event
    - Updates the event
    - Lists events
    - Filters events by actuator_id
    - Verifies 404 behavior for nonexistent events
    - Verifies 404 behavior when creating an event
      for a nonexistent actuator
    """

    # ---------------------------------------------------------
    # 1. Create parent aquaponics system
    # ---------------------------------------------------------
    system_payload = {
        "name": "Test Actuator Event System",
        "description": (
            "System created for actuator event API integration testing."
        ),
        "timezone": "UTC",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/systems",
        json=system_payload,
    )

    print(
        "SYSTEM CREATE RESPONSE:",
        response.status_code,
        response.json(),
    )

    assert response.status_code == 201

    system = response.json()

    assert system["name"] == "Test Actuator Event System"
    assert system["timezone"] == "UTC"
    assert system["is_active"] is True

    system_id = system["id"]

    # ---------------------------------------------------------
    # 2. Create actuator to own the event
    # ---------------------------------------------------------
    actuator_payload = {
        "system_id": system_id,
        "name": "Test Event Pump",
        "actuator_type": "water_pump",
        "control_mode": "manual",
        "hardware_identifier": "PUMP-EVENT-TEST-001",
        "location_type": "tank",
        "is_enabled": True,
        "safety_config": {
            "max_runtime_seconds": 300,
        },
        "current_state": "off",
        "current_value": 0,
    }

    response = await client.post(
        "/api/v1/actuators",
        json=actuator_payload,
    )

    print(
        "ACTUATOR CREATE RESPONSE:",
        response.status_code,
        response.json(),
    )

    assert response.status_code == 201

    actuator = response.json()

    assert actuator["system_id"] == system_id
    assert actuator["name"] == "Test Event Pump"
    assert actuator["actuator_type"] == "water_pump"
    assert actuator["control_mode"] == "manual"
    assert actuator["current_state"] == "off"

    actuator_id = actuator["id"]

    # ---------------------------------------------------------
    # 3. Create actuator event
    # ---------------------------------------------------------
    event_payload = {
        "actuator_id": actuator_id,
        "command_type": "activate",
        "requested_value": 1,
        "actual_value": 1,
        "started_at": "2026-01-01T10:00:00Z",
        "completed_at": "2026-01-01T10:00:01Z",
        "duration_ms": 1000,
        "trigger_source": "manual",
        "status": "completed",
        "fault_code": None,
        "error_message": None,
    }

    response = await client.post(
        "/api/v1/actuator-events",
        json=event_payload,
    )

    print(
        "ACTUATOR EVENT CREATE RESPONSE:",
        response.status_code,
        response.json(),
    )

    assert response.status_code == 201

    event = response.json()

    assert event["actuator_id"] == actuator_id
    assert event["command_type"] == "activate"
    assert event["requested_value"] == 1.0
    assert event["actual_value"] == 1.0
    assert event["duration_ms"] == 1000
    assert event["trigger_source"] == "manual"
    assert event["status"] == "completed"
    assert event["fault_code"] is None
    assert event["error_message"] is None

    event_id = event["id"]

    # ---------------------------------------------------------
    # 4. Get actuator event
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/actuator-events/{event_id}",
    )

    print(
        "ACTUATOR EVENT GET RESPONSE:",
        response.status_code,
        response.json(),
    )

    assert response.status_code == 200

    fetched = response.json()

    assert fetched["id"] == event_id
    assert fetched["actuator_id"] == actuator_id
    assert fetched["command_type"] == "activate"

    # ---------------------------------------------------------
    # 5. Update actuator event
    # ---------------------------------------------------------
    update_payload = {
        "actual_value": 0.95,
        "completed_at": "2026-01-01T10:00:02Z",
        "duration_ms": 2000,
        "status": "failed",
        "fault_code": "PUMP_TIMEOUT",
        "error_message": "Pump did not reach expected state.",
    }

    response = await client.patch(
        f"/api/v1/actuator-events/{event_id}",
        json=update_payload,
    )

    print(
        "ACTUATOR EVENT UPDATE RESPONSE:",
        response.status_code,
        response.json(),
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["id"] == event_id
    assert updated["actuator_id"] == actuator_id
    assert updated["actual_value"] == 0.95
    assert updated["duration_ms"] == 2000
    assert updated["status"] == "failed"
    assert updated["fault_code"] == "PUMP_TIMEOUT"
    assert (
        updated["error_message"]
        == "Pump did not reach expected state."
    )

    # ---------------------------------------------------------
    # 6. List all actuator events
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/actuator-events",
    )

    assert response.status_code == 200

    events = response.json()

    assert isinstance(events, list)

    assert any(
        item["id"] == event_id
        for item in events
    )

    # ---------------------------------------------------------
    # 7. Filter events by actuator_id
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/actuator-events"
        f"?actuator_id={actuator_id}",
    )

    assert response.status_code == 200

    filtered_events = response.json()

    assert filtered_events

    assert all(
        item["actuator_id"] == actuator_id
        for item in filtered_events
    )

    assert any(
        item["id"] == event_id
        for item in filtered_events
    )

    # ---------------------------------------------------------
    # 8. Nonexistent event returns 404
    # ---------------------------------------------------------
    nonexistent_event_id = (
        "00000000-0000-0000-0000-000000000000"
    )

    response = await client.get(
        f"/api/v1/actuator-events/{nonexistent_event_id}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Actuator event not found"

    # ---------------------------------------------------------
    # 9. Creating event with nonexistent actuator returns 404
    # ---------------------------------------------------------
    invalid_event_payload = {
        "actuator_id": nonexistent_event_id,
        "command_type": "activate",
        "requested_value": 1,
        "actual_value": None,
        "started_at": "2026-01-01T11:00:00Z",
        "completed_at": None,
        "duration_ms": None,
        "trigger_source": "manual",
        "status": "pending",
        "fault_code": None,
        "error_message": None,
    }

    response = await client.post(
        "/api/v1/actuator-events",
        json=invalid_event_payload,
    )

    print(
        "INVALID ACTUATOR EVENT RESPONSE:",
        response.status_code,
        response.json(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Actuator not found"