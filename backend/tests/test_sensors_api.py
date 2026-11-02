import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_sensor_create_get_update_delete_flow(
    client: AsyncClient,
):
    """
    Integration test for the sensor lifecycle.

    Creates an aquaponics system first because sensors belong
    to a system through a foreign-key relationship.

    Then creates, retrieves, updates, lists, filters, and
    soft-deletes the sensor.
    """

    # ---------------------------------------------------------
    # 1. Create parent aquaponics system
    # ---------------------------------------------------------
    system_payload = {
        "name": "Test Aquaponics System",
        "description": "System created for sensor API integration testing.",
        "timezone": "UTC",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/systems",
        json=system_payload,
    )

    assert response.status_code == 201

    system = response.json()

    assert system["name"] == "Test Aquaponics System"
    assert system["timezone"] == "UTC"
    assert system["is_active"] is True

    system_id = system["id"]

    # ---------------------------------------------------------
    # 2. Create sensor
    # ---------------------------------------------------------
    create_payload = {
        "system_id": system_id,
        "name": "Test Water Temperature Sensor",
        "sensor_type": "water_temperature",
        "measurement_type": "temperature",
        "location_type": "tank",
        "location_id": None,
        "unit": "°C",
        "hardware_identifier": "TEMP-API-TEST-001",
        "is_simulated": True,
        "is_enabled": True,
        "sampling_interval_seconds": 10,
        "calibration_status": "pending",
    }

    response = await client.post(
        "/api/v1/sensors",
        json=create_payload,
    )

    assert response.status_code == 201

    sensor = response.json()

    assert sensor["system_id"] == system_id
    assert sensor["name"] == "Test Water Temperature Sensor"
    assert sensor["sensor_type"] == "water_temperature"
    assert sensor["measurement_type"] == "temperature"
    assert sensor["location_type"] == "tank"
    assert sensor["unit"] == "°C"
    assert sensor["hardware_identifier"] == "TEMP-API-TEST-001"
    assert sensor["is_simulated"] is True
    assert sensor["is_enabled"] is True
    assert sensor["sampling_interval_seconds"] == 10
    assert sensor["calibration_status"] == "pending"

    sensor_id = sensor["id"]

    # ---------------------------------------------------------
    # 3. Get sensor
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/sensors/{sensor_id}"
    )

    assert response.status_code == 200

    fetched = response.json()

    assert fetched["id"] == sensor_id
    assert fetched["system_id"] == system_id
    assert fetched["name"] == "Test Water Temperature Sensor"

    # ---------------------------------------------------------
    # 4. Update sensor
    # ---------------------------------------------------------
    update_payload = {
        "name": "Updated Water Temperature Sensor",
        "sampling_interval_seconds": 30,
        "is_enabled": True,
        "calibration_status": "verified",
    }

    response = await client.patch(
        f"/api/v1/sensors/{sensor_id}",
        json=update_payload,
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["id"] == sensor_id
    assert updated["system_id"] == system_id
    assert updated["name"] == "Updated Water Temperature Sensor"
    assert updated["sampling_interval_seconds"] == 30
    assert updated["is_enabled"] is True
    assert updated["calibration_status"] == "verified"

    # ---------------------------------------------------------
    # 5. Sensor should appear in normal listing
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/sensors"
    )

    assert response.status_code == 200

    sensors = response.json()

    assert any(
        item["id"] == sensor_id
        for item in sensors
    )

    # ---------------------------------------------------------
    # 6. Filter sensors by system_id
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/sensors?system_id={system_id}"
    )

    assert response.status_code == 200

    filtered_sensors = response.json()

    assert filtered_sensors

    assert all(
        item["system_id"] == system_id
        for item in filtered_sensors
    )

    assert any(
        item["id"] == sensor_id
        for item in filtered_sensors
    )

    # ---------------------------------------------------------
    # 7. Delete sensor
    # ---------------------------------------------------------
    response = await client.delete(
        f"/api/v1/sensors/{sensor_id}"
    )

    assert response.status_code == 204

    # ---------------------------------------------------------
    # 8. Deleted sensor must no longer be accessible
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/sensors/{sensor_id}"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == "Sensor not found"

    # ---------------------------------------------------------
    # 9. Deleted sensor must be excluded from normal listing
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/sensors"
    )

    assert response.status_code == 200

    active_sensors = response.json()

    assert all(
        item["id"] != sensor_id
        for item in active_sensors
    )

    # ---------------------------------------------------------
    # 10. Updating a deleted sensor must fail
    # ---------------------------------------------------------
    response = await client.patch(
        f"/api/v1/sensors/{sensor_id}",
        json={
            "name": "Should Not Update",
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"] == "Sensor not found"