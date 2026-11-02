import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_automation_run_create_get_update_list_filter_flow(
    client: AsyncClient,
):
    """
    Integration test for the automation-run lifecycle.

    Creates the parent system and automation rule first because
    automation runs belong to an automation rule.
    """

    # ---------------------------------------------------------
    # 1. Create parent aquaponics system
    # ---------------------------------------------------------
    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Test Automation Run System",
            "description": (
                "System created for automation run API testing."
            ),
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system = response.json()
    system_id = system["id"]

    # ---------------------------------------------------------
    # 2. Create automation rule
    # ---------------------------------------------------------
    response = await client.post(
        "/api/v1/automation-rules",
        json={
            "system_id": system_id,
            "name": "Test Scheduled Pump Rule",
            "description": "Scheduled pump automation.",
            "trigger_type": "schedule",
            "condition_definition": {
                "schedule": "0 * * * *",
            },
            "action_definition": {
                "action": "activate_actuator",
                "actuator_type": "water_pump",
                "value": 1.0,
            },
            "enabled": True,
            "priority": 5,
            "cooldown_seconds": 60,
        },
    )

    assert response.status_code == 201

    rule = response.json()
    rule_id = rule["id"]

    # ---------------------------------------------------------
    # 3. Create automation run
    # ---------------------------------------------------------
    create_payload = {
        "rule_id": rule_id,
        "started_at": "2026-01-01T12:00:00Z",
        "completed_at": "2026-01-01T12:00:05Z",
        "trigger_value": 1.0,
        "status": "completed",
        "result_summary": "Pump activated successfully.",
        "error_message": None,
    }

    response = await client.post(
        "/api/v1/automation-runs",
        json=create_payload,
    )

    assert response.status_code == 201

    run = response.json()

    assert run["rule_id"] == rule_id
    assert run["started_at"].startswith(
        "2026-01-01T12:00:00"
    )
    assert run["completed_at"].startswith(
        "2026-01-01T12:00:05"
    )
    assert run["trigger_value"] == 1.0
    assert run["status"] == "completed"
    assert run["result_summary"] == (
        "Pump activated successfully."
    )
    assert run["error_message"] is None

    run_id = run["id"]

    # ---------------------------------------------------------
    # 4. Get automation run
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/automation-runs/{run_id}"
    )

    assert response.status_code == 200

    fetched = response.json()

    assert fetched["id"] == run_id
    assert fetched["rule_id"] == rule_id
    assert fetched["status"] == "completed"

    # ---------------------------------------------------------
    # 5. Update automation run
    # ---------------------------------------------------------
    update_payload = {
        "status": "failed",
        "completed_at": "2026-01-01T12:00:10Z",
        "trigger_value": 0.95,
        "result_summary": "Pump failed to reach expected state.",
        "error_message": "PUMP_TIMEOUT",
    }

    response = await client.patch(
        f"/api/v1/automation-runs/{run_id}",
        json=update_payload,
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["id"] == run_id
    assert updated["rule_id"] == rule_id
    assert updated["status"] == "failed"
    assert updated["trigger_value"] == 0.95
    assert updated["result_summary"] == (
        "Pump failed to reach expected state."
    )
    assert updated["error_message"] == "PUMP_TIMEOUT"

    # ---------------------------------------------------------
    # 6. List automation runs
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/automation-runs"
    )

    assert response.status_code == 200

    runs = response.json()

    assert any(
        item["id"] == run_id
        for item in runs
    )

    # ---------------------------------------------------------
    # 7. Filter by rule_id
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/automation-runs",
        params={"rule_id": rule_id},
    )

    assert response.status_code == 200

    filtered_runs = response.json()

    assert filtered_runs

    assert all(
        item["rule_id"] == rule_id
        for item in filtered_runs
    )

    assert any(
        item["id"] == run_id
        for item in filtered_runs
    )

    # ---------------------------------------------------------
    # 8. Nonexistent automation run
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/automation-runs/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Automation run not found"
    )

    # ---------------------------------------------------------
    # 9. Creating run for nonexistent rule
    # ---------------------------------------------------------
    invalid_payload = {
        "rule_id": "00000000-0000-0000-0000-000000000000",
        "started_at": "2026-01-01T12:00:00Z",
        "completed_at": None,
        "trigger_value": None,
        "status": "pending",
        "result_summary": None,
        "error_message": None,
    }

    response = await client.post(
        "/api/v1/automation-runs",
        json=invalid_payload,
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Automation rule not found"
    )

    # ---------------------------------------------------------
    # 10. Delete automation run
    # ---------------------------------------------------------
    response = await client.delete(
        f"/api/v1/automation-runs/{run_id}"
    )

    assert response.status_code == 204

    # ---------------------------------------------------------
    # 11. Deleted run should no longer exist
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/automation-runs/{run_id}"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Automation run not found"
    )

    # ---------------------------------------------------------
    # 12. Updating deleted run must fail
    # ---------------------------------------------------------
    response = await client.patch(
        f"/api/v1/automation-runs/{run_id}",
        json={
            "status": "cancelled",
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Automation run not found"
    )