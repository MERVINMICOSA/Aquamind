import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_automation_rule_create_get_update_list_filter_delete_flow(
    client: AsyncClient,
):
    """
    Integration test for the automation-rule lifecycle.

    Creates the parent aquaponics system first because automation
    rules belong to a system.
    """

    # ---------------------------------------------------------
    # 1. Create parent aquaponics system
    # ---------------------------------------------------------
    system_payload = {
        "name": "Test Automation System",
        "description": "System created for automation rule API testing.",
        "timezone": "UTC",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/systems",
        json=system_payload,
    )

    assert response.status_code == 201

    system = response.json()

    assert system["name"] == "Test Automation System"
    assert system["timezone"] == "UTC"
    assert system["is_active"] is True

    system_id = system["id"]

    # ---------------------------------------------------------
    # 2. Create automation rule
    # ---------------------------------------------------------
    create_payload = {
        "system_id": system_id,
        "name": "Low pH Emergency Pump Rule",
        "description": "Activates the pump when pH becomes too low.",
        "trigger_type": "sensor_threshold",
        "condition_definition": {
            "sensor_type": "ph",
            "measurement_type": "ph",
            "operator": "less_than",
            "value": 6.0,
        },
        "action_definition": {
            "action": "activate_actuator",
            "actuator_type": "water_pump",
            "value": 1.0,
        },
        "enabled": True,
        "priority": 10,
        "cooldown_seconds": 300,
    }

    response = await client.post(
        "/api/v1/automation-rules",
        json=create_payload,
    )

    assert response.status_code == 201

    rule = response.json()

    assert rule["system_id"] == system_id
    assert rule["name"] == "Low pH Emergency Pump Rule"
    assert rule["description"] == (
        "Activates the pump when pH becomes too low."
    )
    assert rule["trigger_type"] == "sensor_threshold"
    assert rule["condition_definition"]["sensor_type"] == "ph"
    assert rule["condition_definition"]["operator"] == "less_than"
    assert rule["condition_definition"]["value"] == 6.0
    assert rule["action_definition"]["action"] == "activate_actuator"
    assert rule["action_definition"]["actuator_type"] == "water_pump"
    assert rule["enabled"] is True
    assert rule["priority"] == 10
    assert rule["cooldown_seconds"] == 300

    rule_id = rule["id"]

    # ---------------------------------------------------------
    # 3. Get automation rule
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/automation-rules/{rule_id}"
    )

    assert response.status_code == 200

    fetched = response.json()

    assert fetched["id"] == rule_id
    assert fetched["system_id"] == system_id
    assert fetched["name"] == "Low pH Emergency Pump Rule"
    assert fetched["trigger_type"] == "sensor_threshold"

    # ---------------------------------------------------------
    # 4. Update automation rule
    # ---------------------------------------------------------
    update_payload = {
        "name": "Updated Low pH Pump Rule",
        "priority": 20,
        "cooldown_seconds": 600,
        "enabled": False,
    }

    response = await client.patch(
        f"/api/v1/automation-rules/{rule_id}",
        json=update_payload,
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["id"] == rule_id
    assert updated["system_id"] == system_id
    assert updated["name"] == "Updated Low pH Pump Rule"
    assert updated["priority"] == 20
    assert updated["cooldown_seconds"] == 600
    assert updated["enabled"] is False

    # ---------------------------------------------------------
    # 5. Normal listing
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/automation-rules"
    )

    assert response.status_code == 200

    rules = response.json()

    assert any(
        item["id"] == rule_id
        for item in rules
    )

    # ---------------------------------------------------------
    # 6. Filter by system_id
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/automation-rules",
        params={"system_id": system_id},
    )

    assert response.status_code == 200

    filtered_rules = response.json()

    assert filtered_rules

    assert all(
        item["system_id"] == system_id
        for item in filtered_rules
    )

    assert any(
        item["id"] == rule_id
        for item in filtered_rules
    )

    # ---------------------------------------------------------
    # 7. Filter by enabled
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/automation-rules",
        params={
            "system_id": system_id,
            "enabled": False,
        },
    )

    assert response.status_code == 200

    disabled_rules = response.json()

    assert any(
        item["id"] == rule_id
        for item in disabled_rules
    )

    assert all(
        item["enabled"] is False
        for item in disabled_rules
    )

    # ---------------------------------------------------------
    # 8. Nonexistent automation rule
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/automation-rules/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Automation rule not found"
    )

    # ---------------------------------------------------------
    # 9. Creating a rule for nonexistent system
    # ---------------------------------------------------------
    invalid_payload = {
        "system_id": "00000000-0000-0000-0000-000000000000",
        "name": "Invalid Rule",
        "description": "This should fail.",
        "trigger_type": "manual",
        "condition_definition": {
            "operator": "manual",
        },
        "action_definition": {
            "action": "activate_actuator",
        },
        "enabled": True,
        "priority": 0,
        "cooldown_seconds": 0,
    }

    response = await client.post(
        "/api/v1/automation-rules",
        json=invalid_payload,
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Aquaponics system not found"
    )

    # ---------------------------------------------------------
    # 10. Delete automation rule
    # ---------------------------------------------------------
    response = await client.delete(
        f"/api/v1/automation-rules/{rule_id}"
    )

    assert response.status_code == 204

    # ---------------------------------------------------------
    # 11. Deleted rule should no longer exist
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/automation-rules/{rule_id}"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Automation rule not found"
    )

    # ---------------------------------------------------------
    # 12. Updating deleted rule must fail
    # ---------------------------------------------------------
    response = await client.patch(
        f"/api/v1/automation-rules/{rule_id}",
        json={
            "name": "Should Not Update",
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Automation rule not found"
    )