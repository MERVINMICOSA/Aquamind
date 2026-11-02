import pytest


@pytest.mark.asyncio
async def test_actuator_create_get_update_delete_flow(client):
    """
    Integration test for the actuator lifecycle.

    Creates an aquaponics system first because actuators belong
    to a system through a foreign-key relationship.

    Then creates, retrieves, updates, lists, filters, and
    soft-deletes the actuator.
    """

    # ---------------------------------------------------------
    # 1. Create parent aquaponics system
    # ---------------------------------------------------------
    system_payload = {
        "name": "Test Actuator System",
        "description": "System created for actuator API integration testing.",
        "timezone": "UTC",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/systems",
        json=system_payload,
    )

    assert response.status_code == 201

    system = response.json()

    assert system["name"] == "Test Actuator System"
    assert system["timezone"] == "UTC"
    assert system["is_active"] is True

    system_id = system["id"]

    # ---------------------------------------------------------
    # 2. Create actuator
    # ---------------------------------------------------------
    create_payload = {
        "system_id": system_id,
        "name": "Test API Water Pump",
        "actuator_type": "water_pump",
        "control_mode": "manual",
        "hardware_identifier": "PUMP-API-TEST-001",
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
        json=create_payload,
    )

    print("ACTUATOR CREATE RESPONSE:", response.status_code, response.json())

    assert response.status_code == 201

    actuator = response.json()

    assert actuator["system_id"] == system_id
    assert actuator["name"] == "Test API Water Pump"
    assert actuator["actuator_type"] == "water_pump"
    assert actuator["current_state"] == "off"
    assert actuator["current_value"] == 0.0
    assert actuator["deleted_at"] is None

    actuator_id = actuator["id"]

    # ---------------------------------------------------------
    # 3. Update actuator
    # ---------------------------------------------------------
    update_payload = {
        "current_state": "on",
        "current_value": 1,
        "is_enabled": True,
    }

    response = await client.patch(
        f"/api/v1/actuators/{actuator_id}",
        json=update_payload,
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["id"] == actuator_id
    assert updated["current_state"] == "on"
    assert updated["current_value"] == 1.0
    assert updated["is_enabled"] is True

    # ---------------------------------------------------------
    # 4. Delete actuator
    # ---------------------------------------------------------
    response = await client.delete(
        f"/api/v1/actuators/{actuator_id}"
    )

    assert response.status_code == 204

    # ---------------------------------------------------------
    # 5. Deleted actuator must no longer be accessible
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/actuators/{actuator_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Actuator not found"

    # ---------------------------------------------------------
    # 6. Deleted actuator must be excluded from normal listing
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/actuators"
    )

    assert response.status_code == 200

    active_actuators = response.json()

    assert all(
        item["id"] != actuator_id
        for item in active_actuators
    )

    # ---------------------------------------------------------
    # 7. Deleted actuator should be visible when requested
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/actuators?include_deleted=true"
    )

    assert response.status_code == 200

    all_actuators = response.json()

    deleted = next(
        item
        for item in all_actuators
        if item["id"] == actuator_id
    )

    assert deleted["deleted_at"] is not None


@pytest.mark.asyncio
async def test_create_actuator_requires_existing_system(client):
    """
    An actuator cannot be created for a system that does not exist.
    """

    payload = {
        "system_id": "00000000-0000-0000-0000-000000000001",
        "name": "Invalid Water Pump",
        "actuator_type": "water_pump",
        "control_mode": "manual",
        "hardware_identifier": "PUMP-INVALID-001",
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
        json=payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Aquaponics system not found"