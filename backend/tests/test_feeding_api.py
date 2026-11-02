import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_feeding_api_full_lifecycle(
    client: AsyncClient,
):
    # =========================================================
    # 1. Create system
    # =========================================================

    system_payload = {
        "name": "Test Feeding System",
        "description": "System created for feeding API testing.",
        "timezone": "UTC",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/systems",
        json=system_payload,
    )

    assert response.status_code == 201

    system = response.json()
    system_id = system["id"]

    # =========================================================
    # 2. Create tank
    # =========================================================

    tank_payload = {
        "system_id": system_id,
        "name": "Test Feeding Tank",
        "capacity_liters": 1000,
        "species": "Tilapia",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/tanks",
        json=tank_payload,
    )

    assert response.status_code == 201

    tank = response.json()
    tank_id = tank["id"]

    # =========================================================
    # 3. Create fish feeder actuator
    # =========================================================

    actuator_payload = {
        "system_id": system_id,
        "name": "Test Fish Feeder",
        "actuator_type": "fish_feeder",
        "control_mode": "scheduled",
        "hardware_identifier": "FEEDER-TEST-001",
        "location_type": "tank",
        "location_id": tank_id,
        "is_enabled": True,
        "safety_config": {
            "max_runtime_seconds": 30,
        },
        "current_state": "off",
        "current_value": None,
        "last_state_at": None,
    }

    response = await client.post(
        "/api/v1/actuators",
        json=actuator_payload,
    )

    assert response.status_code == 201

    actuator = response.json()
    actuator_id = actuator["id"]

    # =========================================================
    # 4. Create feeding schedule
    # =========================================================

    schedule_payload = {
        "system_id": system_id,
        "actuator_id": actuator_id,
        "name": "Morning Feeding",
        "schedule_expression": "0 8 * * *",
        "enabled": True,
        "max_per_feed_grams": 100.0,
    }

    response = await client.post(
        "/api/v1/feeding/schedules",
        json=schedule_payload,
    )

    assert response.status_code == 201

    schedule = response.json()

    assert schedule["system_id"] == system_id
    assert schedule["actuator_id"] == actuator_id
    assert schedule["name"] == "Morning Feeding"
    assert schedule["schedule_expression"] == "0 8 * * *"
    assert schedule["enabled"] is True
    assert schedule["max_per_feed_grams"] == 100.0

    schedule_id = schedule["id"]

    # =========================================================
    # 5. Get feeding schedule
    # =========================================================

    response = await client.get(
        f"/api/v1/feeding/schedules/{schedule_id}"
    )

    assert response.status_code == 200

    fetched_schedule = response.json()

    assert fetched_schedule["id"] == schedule_id
    assert fetched_schedule["name"] == "Morning Feeding"

    # =========================================================
    # 6. Filter feeding schedules
    # =========================================================

    response = await client.get(
        "/api/v1/feeding/schedules",
        params={
            "system_id": system_id,
            "actuator_id": actuator_id,
            "enabled": True,
        },
    )

    assert response.status_code == 200

    schedules = response.json()

    assert any(
        item["id"] == schedule_id
        for item in schedules
    )

    assert all(
        item["system_id"] == system_id
        for item in schedules
    )

    # =========================================================
    # 7. Update feeding schedule
    # =========================================================

    response = await client.patch(
        f"/api/v1/feeding/schedules/{schedule_id}",
        json={
            "name": "Updated Morning Feeding",
            "max_per_feed_grams": 120.0,
            "enabled": False,
        },
    )

    assert response.status_code == 200

    updated_schedule = response.json()

    assert updated_schedule["id"] == schedule_id
    assert updated_schedule["name"] == "Updated Morning Feeding"
    assert updated_schedule["max_per_feed_grams"] == 120.0
    assert updated_schedule["enabled"] is False

    # =========================================================
    # 8. Create feeder calibration
    # =========================================================

    calibration_payload = {
        "actuator_id": actuator_id,
        "run_count": 5,
        "measured_seconds": 10.0,
        "measured_grams": 50.0,
        "grams_per_second": 5.0,
        "calibration_method": "measured_average",
        "performed_at": "2026-01-01T10:00:00Z",
        "verified_by_user_id": None,
        "notes": "Initial feeder calibration.",
    }

    response = await client.post(
        "/api/v1/feeding/calibrations",
        json=calibration_payload,
    )

    assert response.status_code == 201

    calibration = response.json()

    assert calibration["actuator_id"] == actuator_id
    assert calibration["run_count"] == 5
    assert calibration["measured_seconds"] == 10.0
    assert calibration["measured_grams"] == 50.0
    assert calibration["grams_per_second"] == 5.0
    assert calibration["calibration_method"] == "measured_average"

    calibration_id = calibration["id"]

    # =========================================================
    # 9. Get feeder calibration
    # =========================================================

    response = await client.get(
        f"/api/v1/feeding/calibrations/{calibration_id}"
    )

    assert response.status_code == 200

    fetched_calibration = response.json()

    assert fetched_calibration["id"] == calibration_id
    assert fetched_calibration["actuator_id"] == actuator_id

    # =========================================================
    # 10. List/filter feeder calibrations
    # =========================================================

    response = await client.get(
        "/api/v1/feeding/calibrations",
        params={"actuator_id": actuator_id},
    )

    assert response.status_code == 200

    calibrations = response.json()

    assert any(
        item["id"] == calibration_id
        for item in calibrations
    )

    assert all(
        item["actuator_id"] == actuator_id
        for item in calibrations
    )

    # =========================================================
    # 11. Update feeder calibration
    # =========================================================

    response = await client.patch(
        f"/api/v1/feeding/calibrations/{calibration_id}",
        json={
            "grams_per_second": 5.25,
            "notes": "Calibration verified and updated.",
        },
    )

    assert response.status_code == 200

    updated_calibration = response.json()

    assert updated_calibration["grams_per_second"] == 5.25
    assert (
        updated_calibration["notes"]
        == "Calibration verified and updated."
    )

    # =========================================================
    # 12. Create fish population record
    # =========================================================

    population_payload = {
        "tank_id": tank_id,
        "species": "Tilapia",
        "count": 100,
        "estimated_biomass_grams": 25000.0,
        "effective_at": "2026-01-01T09:00:00Z",
        "recorded_by_user_id": None,
        "notes": "Initial population record.",
    }

    response = await client.post(
        "/api/v1/feeding/population",
        json=population_payload,
    )

    assert response.status_code == 201

    population = response.json()

    assert population["tank_id"] == tank_id
    assert population["species"] == "Tilapia"
    assert population["count"] == 100
    assert population["estimated_biomass_grams"] == 25000.0

    population_id = population["id"]

    # =========================================================
    # 13. Get population record
    # =========================================================

    response = await client.get(
        f"/api/v1/feeding/population/{population_id}"
    )

    assert response.status_code == 200

    fetched_population = response.json()

    assert fetched_population["id"] == population_id
    assert fetched_population["tank_id"] == tank_id

    # =========================================================
    # 14. Filter population records
    # =========================================================

    response = await client.get(
        "/api/v1/feeding/population",
        params={"tank_id": tank_id},
    )

    assert response.status_code == 200

    populations = response.json()

    assert any(
        item["id"] == population_id
        for item in populations
    )

    assert all(
        item["tank_id"] == tank_id
        for item in populations
    )

    # =========================================================
    # 15. Update population record
    # =========================================================

    response = await client.patch(
        f"/api/v1/feeding/population/{population_id}",
        json={
            "count": 95,
            "estimated_biomass_grams": 24000.0,
            "notes": "Population updated after sampling.",
        },
    )

    assert response.status_code == 200

    updated_population = response.json()

    assert updated_population["count"] == 95
    assert updated_population["estimated_biomass_grams"] == 24000.0
    assert (
        updated_population["notes"]
        == "Population updated after sampling."
    )

    # =========================================================
    # 16. Create actuator event
    # =========================================================

    actuator_event_payload = {
        "actuator_id": actuator_id,
        "command_type": "activate",
        "requested_value": 10.0,
        "actual_value": 10.0,
        "started_at": "2026-01-01T08:00:00Z",
        "completed_at": "2026-01-01T08:00:10Z",
        "duration_ms": 10000,
        "trigger_source": "schedule",
        "status": "completed",
        "fault_code": None,
        "error_message": None,
    }

    response = await client.post(
        "/api/v1/actuator-events",
        json=actuator_event_payload,
    )

    assert response.status_code == 201

    actuator_event = response.json()
    actuator_event_id = actuator_event["id"]

    # =========================================================
    # 17. Create feeding event
    # =========================================================

    feeding_event_payload = {
        "schedule_id": schedule_id,
        "actuator_event_id": actuator_event_id,
        "tank_id": tank_id,
        "amount_grams": 50.0,
        "duration_seconds": 10.0,
        "calculated_from_biomass": 25000.0,
        "calibration_id": calibration_id,
        "executed_at": "2026-01-01T08:00:10Z",
        "status": "completed",
        "notes": "Scheduled morning feeding.",
    }

    response = await client.post(
        "/api/v1/feeding/events",
        json=feeding_event_payload,
    )

    assert response.status_code == 201

    feeding_event = response.json()

    assert feeding_event["schedule_id"] == schedule_id
    assert feeding_event["actuator_event_id"] == actuator_event_id
    assert feeding_event["tank_id"] == tank_id
    assert feeding_event["amount_grams"] == 50.0
    assert feeding_event["duration_seconds"] == 10.0
    assert feeding_event["calculated_from_biomass"] == 25000.0
    assert feeding_event["calibration_id"] == calibration_id
    assert feeding_event["status"] == "completed"

    feeding_event_id = feeding_event["id"]

    # =========================================================
    # 18. Get feeding event
    # =========================================================

    response = await client.get(
        f"/api/v1/feeding/events/{feeding_event_id}"
    )

    assert response.status_code == 200

    fetched_event = response.json()

    assert fetched_event["id"] == feeding_event_id
    assert fetched_event["tank_id"] == tank_id
    assert fetched_event["status"] == "completed"

    # =========================================================
    # 19. Filter feeding events
    # =========================================================

    response = await client.get(
        "/api/v1/feeding/events",
        params={
            "tank_id": tank_id,
            "schedule_id": schedule_id,
            "status_filter": "completed",
        },
    )

    assert response.status_code == 200

    events = response.json()

    assert any(
        item["id"] == feeding_event_id
        for item in events
    )

    assert all(
        item["tank_id"] == tank_id
        for item in events
    )

    assert all(
        item["schedule_id"] == schedule_id
        for item in events
    )

    assert all(
        item["status"] == "completed"
        for item in events
    )

    # =========================================================
    # 20. Update feeding event
    # =========================================================

    response = await client.patch(
        f"/api/v1/feeding/events/{feeding_event_id}",
        json={
            "amount_grams": 55.0,
            "duration_seconds": 11.0,
            "notes": "Feeding event updated.",
        },
    )

    assert response.status_code == 200

    updated_event = response.json()

    assert updated_event["amount_grams"] == 55.0
    assert updated_event["duration_seconds"] == 11.0
    assert updated_event["notes"] == "Feeding event updated."

    # =========================================================
    # 21. Invalid schedule actuator relationship
    # =========================================================

    response = await client.post(
        "/api/v1/feeding/schedules",
        json={
            "system_id": "00000000-0000-0000-0000-000000000000",
            "actuator_id": actuator_id,
            "name": "Invalid Schedule",
            "schedule_expression": "0 9 * * *",
            "enabled": True,
            "max_per_feed_grams": 50.0,
        },
    )

    assert response.status_code == 404

    # =========================================================
    # 22. Nonexistent schedule
    # =========================================================

    response = await client.get(
        "/api/v1/feeding/schedules/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Feeding schedule not found"
    )

    # =========================================================
    # 23. Nonexistent calibration
    # =========================================================

    response = await client.get(
        "/api/v1/feeding/calibrations/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Feeder calibration not found"
    )

    # =========================================================
    # 24. Nonexistent population record
    # =========================================================

    response = await client.get(
        "/api/v1/feeding/population/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Fish population record not found"
    )

    # =========================================================
    # 25. Nonexistent feeding event
    # =========================================================

    response = await client.get(
        "/api/v1/feeding/events/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Feeding event not found"
    )

    # =========================================================
    # 26. Delete feeding event
    # =========================================================

    response = await client.delete(
        f"/api/v1/feeding/events/{feeding_event_id}"
    )

    assert response.status_code == 204

    response = await client.get(
        f"/api/v1/feeding/events/{feeding_event_id}"
    )

    assert response.status_code == 404

    # =========================================================
    # 27. Delete population record
    # =========================================================

    response = await client.delete(
        f"/api/v1/feeding/population/{population_id}"
    )

    assert response.status_code == 204

    response = await client.get(
        f"/api/v1/feeding/population/{population_id}"
    )

    assert response.status_code == 404

    # =========================================================
    # 28. Delete feeder calibration
    # =========================================================

    response = await client.delete(
        f"/api/v1/feeding/calibrations/{calibration_id}"
    )

    assert response.status_code == 204

    response = await client.get(
        f"/api/v1/feeding/calibrations/{calibration_id}"
    )

    assert response.status_code == 404

    # =========================================================
    # 29. Delete feeding schedule
    # =========================================================

    response = await client.delete(
        f"/api/v1/feeding/schedules/{schedule_id}"
    )

    assert response.status_code == 204

    response = await client.get(
        f"/api/v1/feeding/schedules/{schedule_id}"
    )

    assert response.status_code == 404