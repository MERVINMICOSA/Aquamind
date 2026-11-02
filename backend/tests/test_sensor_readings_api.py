import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_sensor_reading_create_get_list_and_filter_flow(
    client: AsyncClient,
):
    """
    Integration test for the sensor-reading lifecycle.

    Creates the parent system and sensor first, then creates,
    retrieves, lists, and filters a sensor reading.
    """

    # ---------------------------------------------------------
    # 1. Create parent aquaponics system
    # ---------------------------------------------------------
    system_payload = {
        "name": "Test Sensor Reading System",
        "description": "System created for sensor reading API testing.",
        "timezone": "UTC",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/systems",
        json=system_payload,
    )

    assert response.status_code == 201

    system = response.json()

    assert system["name"] == "Test Sensor Reading System"
    assert system["timezone"] == "UTC"
    assert system["is_active"] is True

    system_id = system["id"]

    # ---------------------------------------------------------
    # 2. Create sensor
    # ---------------------------------------------------------
    sensor_payload = {
        "system_id": system_id,
        "name": "Test pH Sensor",
        "sensor_type": "ph",
        "measurement_type": "ph",
        "location_type": "tank",
        "location_id": None,
        "unit": "pH",
        "hardware_identifier": "PH-API-TEST-001",
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
    assert sensor["name"] == "Test pH Sensor"
    assert sensor["sensor_type"] == "ph"
    assert sensor["measurement_type"] == "ph"
    assert sensor["unit"] == "pH"
    assert sensor["is_enabled"] is True

    sensor_id = sensor["id"]

    # ---------------------------------------------------------
    # 3. Create sensor reading
    # ---------------------------------------------------------
    reading_payload = {
        "sensor_id": sensor_id,
        "recorded_at": "2026-01-01T12:00:00Z",
        "value_numeric": 7.25,
        "unit": "pH",
        "quality_status": "good",
        "source": "simulator",
        "sequence_number": 1,
    }

    response = await client.post(
        "/api/v1/sensor-readings",
        json=reading_payload,
    )

    assert response.status_code == 201

    reading = response.json()

    assert reading["sensor_id"] == sensor_id
    assert reading["recorded_at"].startswith("2026-01-01T12:00:00")
    assert reading["value_numeric"] == 7.25
    assert reading["unit"] == "pH"
    assert reading["quality_status"] == "good"
    assert reading["source"] == "simulator"
    assert reading["sequence_number"] == 1

    reading_id = reading["id"]

    # ---------------------------------------------------------
    # 4. Get reading
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/sensor-readings/{reading_id}"
    )

    assert response.status_code == 200

    fetched = response.json()

    assert fetched["id"] == reading_id
    assert fetched["sensor_id"] == sensor_id
    assert fetched["value_numeric"] == 7.25

    # ---------------------------------------------------------
    # 5. List readings
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/sensor-readings"
    )

    assert response.status_code == 200

    readings = response.json()

    assert any(
        item["id"] == reading_id
        for item in readings
    )

    # ---------------------------------------------------------
    # 6. Filter readings by sensor_id
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/sensor-readings",
        params={"sensor_id": sensor_id},
    )

    assert response.status_code == 200

    filtered_readings = response.json()

    assert filtered_readings

    assert all(
        item["sensor_id"] == sensor_id
        for item in filtered_readings
    )

    assert any(
        item["id"] == reading_id
        for item in filtered_readings
    )

    # ---------------------------------------------------------
    # 7. Nonexistent reading should return 404
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/sensor-readings/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Sensor reading not found"

    # ---------------------------------------------------------
    # 8. Nonexistent sensor should reject reading creation
    # ---------------------------------------------------------
    invalid_payload = {
        "sensor_id": "00000000-0000-0000-0000-000000000000",
        "recorded_at": "2026-01-01T12:01:00Z",
        "value_numeric": 7.30,
        "unit": "pH",
        "quality_status": "good",
        "source": "simulator",
        "sequence_number": 2,
    }

    response = await client.post(
        "/api/v1/sensor-readings",
        json=invalid_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Sensor not found"


@pytest.mark.asyncio
async def test_disabled_sensor_rejects_sensor_reading(
    client: AsyncClient,
):
    """
    A disabled sensor must not accept new readings.
    """

    # ---------------------------------------------------------
    # 1. Create system
    # ---------------------------------------------------------
    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Disabled Sensor Test System",
            "description": None,
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system_id = response.json()["id"]

    # ---------------------------------------------------------
    # 2. Create disabled sensor
    # ---------------------------------------------------------
    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": "Disabled pH Sensor",
            "sensor_type": "ph",
            "measurement_type": "ph",
            "location_type": "tank",
            "location_id": None,
            "unit": "pH",
            "hardware_identifier": "PH-DISABLED-TEST-001",
            "is_simulated": True,
            "is_enabled": False,
            "sampling_interval_seconds": 10,
            "calibration_status": "pending",
        },
    )

    assert response.status_code == 201

    sensor_id = response.json()["id"]

    # ---------------------------------------------------------
    # 3. Attempt to create reading
    # ---------------------------------------------------------
    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": sensor_id,
            "recorded_at": "2026-01-01T12:00:00Z",
            "value_numeric": 7.25,
            "unit": "pH",
            "quality_status": "good",
            "source": "simulator",
            "sequence_number": 1,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Sensor is disabled"

@pytest.mark.asyncio
async def test_deleted_sensor_rejects_sensor_reading(
    client: AsyncClient,
):
    """
    A soft-deleted sensor must not accept new readings.
    """

    # ---------------------------------------------------------
    # 1. Create system
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Deleted Sensor Reading Test System",
            "description": "System for testing deleted sensors.",
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system_id = response.json()["id"]

    # ---------------------------------------------------------
    # 2. Create sensor
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": "Sensor To Delete",
            "sensor_type": "ph",
            "measurement_type": "ph",
            "location_type": "tank",
            "location_id": None,
            "unit": "pH",
            "hardware_identifier": "PH-DELETED-TEST-001",
            "is_simulated": True,
            "is_enabled": True,
            "sampling_interval_seconds": 10,
            "calibration_status": "pending",
        },
    )

    assert response.status_code == 201

    sensor_id = response.json()["id"]

    # ---------------------------------------------------------
    # 3. Soft-delete sensor
    # ---------------------------------------------------------

    response = await client.delete(
        f"/api/v1/sensors/{sensor_id}"
    )

    assert response.status_code == 204

    # ---------------------------------------------------------
    # 4. Attempt to create reading for deleted sensor
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": sensor_id,
            "recorded_at": "2026-01-01T12:00:00Z",
            "value_numeric": 7.25,
            "unit": "pH",
            "quality_status": "good",
            "source": "simulator",
            "sequence_number": 1,
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"] == "Sensor not found"

@pytest.mark.asyncio
async def test_latest_sensor_readings_returns_one_newest_reading_per_sensor(
    client: AsyncClient,
):
    # ---------------------------------------------------------
    # SYSTEM
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Latest Reading Test System",
            "description": None,
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system_id = response.json()["id"]

    # ---------------------------------------------------------
    # PH SENSOR
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": "Latest pH Sensor",
            "sensor_type": "ph",
            "measurement_type": "ph",
            "location_type": "tank",
            "location_id": None,
            "unit": "pH",
            "hardware_identifier": (
                "LATEST-PH-001"
            ),
            "is_simulated": True,
            "is_enabled": True,
            "sampling_interval_seconds": 10,
            "calibration_status": "pending",
        },
    )

    assert response.status_code == 201

    ph_sensor_id = response.json()["id"]

    # ---------------------------------------------------------
    # TEMPERATURE SENSOR
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": "Latest Temperature Sensor",
            "sensor_type": "water_temperature",
            "measurement_type": "temperature",
            "location_type": "tank",
            "location_id": None,
            "unit": "C",
            "hardware_identifier": (
                "LATEST-TEMP-001"
            ),
            "is_simulated": True,
            "is_enabled": True,
            "sampling_interval_seconds": 10,
            "calibration_status": "pending",
        },
    )

    assert response.status_code == 201

    temperature_sensor_id = (
        response.json()["id"]
    )

    # ---------------------------------------------------------
    # TWO PH READINGS
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": ph_sensor_id,
            "recorded_at": (
                "2026-09-06T01:00:00Z"
            ),
            "value_numeric": 6.8,
            "unit": "pH",
            "quality_status": "good",
            "source": "simulator",
            "sequence_number": 1,
        },
    )

    assert response.status_code == 201

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": ph_sensor_id,
            "recorded_at": (
                "2026-09-06T02:00:00Z"
            ),
            "value_numeric": 7.1,
            "unit": "pH",
            "quality_status": "good",
            "source": "simulator",
            "sequence_number": 2,
        },
    )

    assert response.status_code == 201

    # ---------------------------------------------------------
    # TEMPERATURE READING
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": (
                temperature_sensor_id
            ),
            "recorded_at": (
                "2026-09-06T01:30:00Z"
            ),
            "value_numeric": 26.4,
            "unit": "C",
            "quality_status": "good",
            "source": "simulator",
            "sequence_number": 1,
        },
    )

    assert response.status_code == 201

    # ---------------------------------------------------------
    # LATEST
    # ---------------------------------------------------------

    response = await client.get(
        "/api/v1/sensor-readings/latest",
        params={
            "system_id": system_id,
        },
    )

    assert response.status_code == 200

    readings = response.json()

    assert len(readings) == 2

    readings_by_sensor = {
        item["sensor_id"]: item
        for item in readings
    }

    assert (
        readings_by_sensor[
            ph_sensor_id
        ]["value_numeric"]
        == 7.1
    )

    assert (
        readings_by_sensor[
            ph_sensor_id
        ]["sequence_number"]
        == 2
    )

    assert (
        readings_by_sensor[
            temperature_sensor_id
        ]["value_numeric"]
        == 26.4
    )


@pytest.mark.asyncio
async def test_latest_sensor_readings_returns_empty_when_sensors_have_no_readings(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "No Latest Reading System",
            "description": None,
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system_id = response.json()["id"]

    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": "No Reading pH Sensor",
            "sensor_type": "ph",
            "measurement_type": "ph",
            "location_type": "tank",
            "location_id": None,
            "unit": "pH",
            "hardware_identifier": (
                "NO-LATEST-PH-001"
            ),
            "is_simulated": True,
            "is_enabled": True,
            "sampling_interval_seconds": 10,
            "calibration_status": "pending",
        },
    )

    assert response.status_code == 201

    response = await client.get(
        "/api/v1/sensor-readings/latest",
        params={
            "system_id": system_id,
        },
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_latest_sensor_readings_excludes_soft_deleted_sensors(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Deleted Latest Sensor System",
            "description": None,
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system_id = response.json()["id"]

    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": "Deleted Latest pH Sensor",
            "sensor_type": "ph",
            "measurement_type": "ph",
            "location_type": "tank",
            "location_id": None,
            "unit": "pH",
            "hardware_identifier": (
                "DELETED-LATEST-PH-001"
            ),
            "is_simulated": True,
            "is_enabled": True,
            "sampling_interval_seconds": 10,
            "calibration_status": "pending",
        },
    )

    assert response.status_code == 201

    sensor_id = response.json()["id"]

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": sensor_id,
            "recorded_at": (
                "2026-09-06T03:00:00Z"
            ),
            "value_numeric": 7.0,
            "unit": "pH",
            "quality_status": "good",
            "source": "simulator",
            "sequence_number": 1,
        },
    )

    assert response.status_code == 201

    response = await client.delete(
        f"/api/v1/sensors/{sensor_id}"
    )

    assert response.status_code == 204

    response = await client.get(
        "/api/v1/sensor-readings/latest",
        params={
            "system_id": system_id,
        },
    )

    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_sensor_reading_history_is_bounded_and_newest_first(
    client: AsyncClient,
):
    # ---------------------------------------------------------
    # SYSTEM
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Sensor History Test System",
            "description": None,
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system_id = response.json()["id"]

    # ---------------------------------------------------------
    # SENSOR
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": "History pH Sensor",
            "sensor_type": "ph",
            "measurement_type": "ph",
            "location_type": "tank",
            "location_id": None,
            "unit": "pH",
            "hardware_identifier": (
                "HISTORY-PH-001"
            ),
            "is_simulated": True,
            "is_enabled": True,
            "sampling_interval_seconds": 60,
            "calibration_status": "pending",
        },
    )

    assert response.status_code == 201

    sensor_id = response.json()["id"]

    # ---------------------------------------------------------
    # THREE READINGS
    # ---------------------------------------------------------

    readings = [
        (
            "2026-09-06T01:00:00Z",
            6.8,
            1,
        ),
        (
            "2026-09-06T02:00:00Z",
            7.0,
            2,
        ),
        (
            "2026-09-06T03:00:00Z",
            7.2,
            3,
        ),
    ]

    for (
        recorded_at,
        value_numeric,
        sequence_number,
    ) in readings:
        response = await client.post(
            "/api/v1/sensor-readings",
            json={
                "sensor_id": sensor_id,
                "recorded_at": recorded_at,
                "value_numeric": value_numeric,
                "unit": "pH",
                "quality_status": "good",
                "source": "simulator",
                "sequence_number": sequence_number,
            },
        )

        assert response.status_code == 201

    # ---------------------------------------------------------
    # FIRST TWO NEWEST
    # ---------------------------------------------------------

    response = await client.get(
        "/api/v1/sensor-readings/history",
        params={
            "sensor_id": sensor_id,
            "limit": 2,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 2

    assert [
        item["value_numeric"]
        for item in history
    ] == [
        7.2,
        7.0,
    ]

    assert [
        item["sequence_number"]
        for item in history
    ] == [
        3,
        2,
    ]

@pytest.mark.asyncio
async def test_sensor_reading_history_supports_offset_pagination(
    client: AsyncClient,
):
    # ---------------------------------------------------------
    # SYSTEM
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Sensor History Pagination System",
            "description": None,
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system_id = response.json()["id"]

    # ---------------------------------------------------------
    # SENSOR
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": "Pagination pH Sensor",
            "sensor_type": "ph",
            "measurement_type": "ph",
            "location_type": "tank",
            "location_id": None,
            "unit": "pH",
            "hardware_identifier": (
                "HISTORY-PAGE-PH-001"
            ),
            "is_simulated": True,
            "is_enabled": True,
            "sampling_interval_seconds": 60,
            "calibration_status": "pending",
        },
    )

    assert response.status_code == 201

    sensor_id = response.json()["id"]

    # ---------------------------------------------------------
    # THREE READINGS
    # ---------------------------------------------------------

    for sequence_number in range(
        1,
        4,
    ):
        response = await client.post(
            "/api/v1/sensor-readings",
            json={
                "sensor_id": sensor_id,
                "recorded_at": (
                    f"2026-09-06T0"
                    f"{sequence_number}:00:00Z"
                ),
                "value_numeric": (
                    6.5 +
                    sequence_number / 10
                ),
                "unit": "pH",
                "quality_status": "good",
                "source": "simulator",
                "sequence_number": (
                    sequence_number
                ),
            },
        )

        assert response.status_code == 201

    # ---------------------------------------------------------
    # PAGE 1
    # ---------------------------------------------------------

    response = await client.get(
        "/api/v1/sensor-readings/history",
        params={
            "sensor_id": sensor_id,
            "limit": 2,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    first_page = response.json()

    assert [
        item["sequence_number"]
        for item in first_page
    ] == [
        3,
        2,
    ]

    # ---------------------------------------------------------
    # PAGE 2
    # ---------------------------------------------------------

    response = await client.get(
        "/api/v1/sensor-readings/history",
        params={
            "sensor_id": sensor_id,
            "limit": 2,
            "offset": 2,
        },
    )

    assert response.status_code == 200

    second_page = response.json()

    assert [
        item["sequence_number"]
        for item in second_page
    ] == [
        1,
    ]

@pytest.mark.asyncio
async def test_sensor_reading_history_rejects_limit_above_maximum(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/sensor-readings/history",
        params={
            "sensor_id": (
                "00000000-0000-0000-0000-000000000000"
            ),
            "limit": 101,
        },
    )

    assert response.status_code == 422