import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_sensor_calibration_create_get_update_list_and_filter_flow(
    client: AsyncClient,
):
    """
    Integration test for the sensor calibration lifecycle.

    Creates the parent system and sensor first, then creates,
    retrieves, updates, lists, and filters a sensor calibration.
    """

    # ---------------------------------------------------------
    # 1. Create parent aquaponics system
    # ---------------------------------------------------------
    system_payload = {
        "name": "Test Sensor Calibration System",
        "description": "System created for sensor calibration API testing.",
        "timezone": "UTC",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/systems",
        json=system_payload,
    )

    assert response.status_code == 201

    system = response.json()

    assert system["name"] == "Test Sensor Calibration System"
    assert system["timezone"] == "UTC"
    assert system["is_active"] is True

    system_id = system["id"]

    # ---------------------------------------------------------
    # 2. Create sensor
    # ---------------------------------------------------------
    sensor_payload = {
        "system_id": system_id,
        "name": "Test Calibration pH Sensor",
        "sensor_type": "ph",
        "measurement_type": "ph",
        "location_type": "tank",
        "location_id": None,
        "unit": "pH",
        "hardware_identifier": "PH-CAL-TEST-001",
        "is_simulated": True,
        "is_enabled": True,
        "sampling_interval_seconds": 10,
        "calibration_status": "pending",
    }

    response = await client.post(
        "/api/v1/sensors",
        json=sensor_payload,
    )

    assert response.status_code == 201

    sensor = response.json()

    assert sensor["system_id"] == system_id
    assert sensor["name"] == "Test Calibration pH Sensor"
    assert sensor["sensor_type"] == "ph"
    assert sensor["measurement_type"] == "ph"

    sensor_id = sensor["id"]

    # ---------------------------------------------------------
    # 3. Create sensor calibration
    # ---------------------------------------------------------
    calibration_payload = {
        "sensor_id": sensor_id,
        "offset": 0.15,
        "factor": 1.02,
        "calibration_data": {
            "reference_value": 7.00,
            "measured_value": 6.85,
            "instrument": "laboratory_reference",
        },
        "performed_at": "2026-01-01T10:00:00Z",
        "verified_by_user_id": None,
        "status": "verified",
        "notes": "Initial pH sensor calibration.",
    }

    response = await client.post(
        "/api/v1/sensor-calibrations",
        json=calibration_payload,
    )

    assert response.status_code == 201

    calibration = response.json()

    assert calibration["sensor_id"] == sensor_id
    assert calibration["offset"] == 0.15
    assert calibration["factor"] == 1.02
    assert calibration["calibration_data"]["reference_value"] == 7.00
    assert calibration["calibration_data"]["measured_value"] == 6.85
    assert calibration["performed_at"].startswith(
        "2026-01-01T10:00:00"
    )
    assert calibration["verified_by_user_id"] is None
    assert calibration["status"] == "verified"
    assert calibration["notes"] == "Initial pH sensor calibration."

    calibration_id = calibration["id"]

    # ---------------------------------------------------------
    # 4. Get calibration
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/sensor-calibrations/{calibration_id}"
    )

    assert response.status_code == 200

    fetched = response.json()

    assert fetched["id"] == calibration_id
    assert fetched["sensor_id"] == sensor_id
    assert fetched["offset"] == 0.15
    assert fetched["factor"] == 1.02
    assert fetched["status"] == "verified"

    # ---------------------------------------------------------
    # 5. Update calibration
    # ---------------------------------------------------------
    update_payload = {
        "offset": 0.10,
        "factor": 1.01,
        "status": "verified",
        "notes": "Calibration updated after verification.",
    }

    response = await client.patch(
        f"/api/v1/sensor-calibrations/{calibration_id}",
        json=update_payload,
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["id"] == calibration_id
    assert updated["sensor_id"] == sensor_id
    assert updated["offset"] == 0.10
    assert updated["factor"] == 1.01
    assert updated["status"] == "verified"
    assert (
        updated["notes"]
        == "Calibration updated after verification."
    )

    # ---------------------------------------------------------
    # 6. List calibrations
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/sensor-calibrations"
    )

    assert response.status_code == 200

    calibrations = response.json()

    assert any(
        item["id"] == calibration_id
        for item in calibrations
    )

    # ---------------------------------------------------------
    # 7. Filter calibrations by sensor_id
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/sensor-calibrations",
        params={"sensor_id": sensor_id},
    )

    assert response.status_code == 200

    filtered_calibrations = response.json()

    assert filtered_calibrations

    assert all(
        item["sensor_id"] == sensor_id
        for item in filtered_calibrations
    )

    assert any(
        item["id"] == calibration_id
        for item in filtered_calibrations
    )

    # ---------------------------------------------------------
    # 8. Nonexistent calibration returns 404
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/sensor-calibrations/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Sensor calibration not found"
    )

    # ---------------------------------------------------------
    # 9. Calibration for nonexistent sensor returns 404
    # ---------------------------------------------------------
    invalid_payload = {
        "sensor_id": "00000000-0000-0000-0000-000000000000",
        "offset": 0.0,
        "factor": 1.0,
        "calibration_data": None,
        "performed_at": "2026-01-01T11:00:00Z",
        "verified_by_user_id": None,
        "status": "pending",
        "notes": "Invalid calibration.",
    }

    response = await client.post(
        "/api/v1/sensor-calibrations",
        json=invalid_payload,
    )

    assert response.status_code == 404

    assert response.json()["detail"] == "Sensor not found"

    # ---------------------------------------------------------
    # 10. Delete calibration
    # ---------------------------------------------------------
    response = await client.delete(
        f"/api/v1/sensor-calibrations/{calibration_id}"
    )

    assert response.status_code == 204

    # ---------------------------------------------------------
    # 11. Deleted calibration should no longer exist
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/sensor-calibrations/{calibration_id}"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Sensor calibration not found"
    )