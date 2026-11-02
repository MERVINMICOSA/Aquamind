from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.db.enums import (
    AlertSeverity,
    AlertStatus,
    CalibrationStatus,
    LocationType,
    MeasurementType,
    ReadingQuality,
    ReadingSource,
    SensorType,
)
from app.models.alerts import Alert, AlertThreshold
from app.models.sensors import Sensor
from app.models.system import AquaponicsSystem


async def create_system(session):
    system = AquaponicsSystem(
        name="API Alert Integration System",
    )

    session.add(system)
    await session.commit()
    await session.refresh(system)

    return system


async def create_sensor(session, system):
    sensor = Sensor(
        system_id=system.id,
        name="API Test pH Sensor",
        sensor_type=SensorType.PH,
        measurement_type=MeasurementType.PH,
        location_type=LocationType.SYSTEM,
        unit="pH",
        is_simulated=True,
        is_enabled=True,
        sampling_interval_seconds=60,
        calibration_status=CalibrationStatus.VERIFIED,
    )

    session.add(sensor)
    await session.commit()
    await session.refresh(sensor)

    return sensor


async def create_threshold(
    session,
    *,
    warning_low=6.5,
    warning_high=7.5,
    critical_low=6.0,
    critical_high=8.0,
    cooldown_seconds=900,
    enabled=True,
):
    threshold = AlertThreshold(
        sensor_type=SensorType.PH,
        measurement_type=MeasurementType.PH,
        warning_low=warning_low,
        warning_high=warning_high,
        critical_low=critical_low,
        critical_high=critical_high,
        cooldown_seconds=cooldown_seconds,
        enabled=enabled,
        updated_at=datetime.now(timezone.utc),
    )

    session.add(threshold)
    await session.commit()
    await session.refresh(threshold)

    return threshold


async def create_sensor_and_threshold(
    test_session,
):
    system = await create_system(test_session)
    sensor = await create_sensor(test_session, system)
    threshold = await create_threshold(test_session)

    return system, sensor, threshold


# ============================================================
# WARNING ALERT THROUGH HTTP API
# ============================================================

@pytest.mark.asyncio
async def test_post_warning_sensor_reading_creates_alert(
    client,
    test_session,
):
    system, sensor, threshold = await create_sensor_and_threshold(
        test_session,
    )

    recorded_at = datetime.now(timezone.utc)

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": str(sensor.id),
            "recorded_at": recorded_at.isoformat(),
            "value_numeric": 6.3,
            "unit": "pH",
            "quality_status": ReadingQuality.GOOD.value,
            "source": ReadingSource.SIMULATOR.value,
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["sensor_id"] == str(sensor.id)
    assert float(body["value_numeric"]) == 6.3

    result = await test_session.execute(
        select(Alert).where(
            Alert.sensor_id == sensor.id,
        )
    )

    alerts = result.scalars().all()

    assert len(alerts) == 1

    alert = alerts[0]

    assert alert.system_id == system.id
    assert alert.sensor_id == sensor.id
    assert alert.threshold_id == threshold.id
    assert alert.severity == AlertSeverity.WARNING
    assert alert.status == AlertStatus.ACTIVE
    assert float(alert.trigger_value) == 6.3


# ============================================================
# CRITICAL ALERT THROUGH HTTP API
# ============================================================

@pytest.mark.asyncio
async def test_post_critical_sensor_reading_creates_alert(
    client,
    test_session,
):
    system, sensor, threshold = await create_sensor_and_threshold(
        test_session,
    )

    recorded_at = datetime.now(timezone.utc)

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": str(sensor.id),
            "recorded_at": recorded_at.isoformat(),
            "value_numeric": 5.5,
            "unit": "pH",
            "quality_status": ReadingQuality.GOOD.value,
            "source": ReadingSource.SIMULATOR.value,
        },
    )

    assert response.status_code == 201

    result = await test_session.execute(
        select(Alert).where(
            Alert.sensor_id == sensor.id,
        )
    )

    alerts = result.scalars().all()

    assert len(alerts) == 1

    alert = alerts[0]

    assert alert.system_id == system.id
    assert alert.sensor_id == sensor.id
    assert alert.threshold_id == threshold.id
    assert alert.severity == AlertSeverity.CRITICAL
    assert alert.status == AlertStatus.ACTIVE
    assert float(alert.trigger_value) == 5.5


# ============================================================
# NORMAL READING THROUGH HTTP API
# ============================================================

@pytest.mark.asyncio
async def test_post_normal_sensor_reading_does_not_create_alert(
    client,
    test_session,
):
    _, sensor, _ = await create_sensor_and_threshold(
        test_session,
    )

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": str(sensor.id),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "value_numeric": 7.0,
            "unit": "pH",
            "quality_status": ReadingQuality.GOOD.value,
            "source": ReadingSource.SIMULATOR.value,
        },
    )

    assert response.status_code == 201

    result = await test_session.execute(
        select(Alert).where(
            Alert.sensor_id == sensor.id,
        )
    )

    alerts = result.scalars().all()

    assert alerts == []


# ============================================================
# FAILED READING THROUGH HTTP API
# ============================================================

@pytest.mark.asyncio
async def test_post_failed_quality_reading_does_not_create_alert(
    client,
    test_session,
):
    _, sensor, _ = await create_sensor_and_threshold(
        test_session,
    )

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": str(sensor.id),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "value_numeric": 5.0,
            "unit": "pH",
            "quality_status": ReadingQuality.FAIL.value,
            "source": ReadingSource.SIMULATOR.value,
        },
    )

    assert response.status_code == 201

    result = await test_session.execute(
        select(Alert).where(
            Alert.sensor_id == sensor.id,
        )
    )

    alerts = result.scalars().all()

    assert alerts == []


# ============================================================
# DISABLED THRESHOLD THROUGH HTTP API
# ============================================================

@pytest.mark.asyncio
async def test_post_reading_with_disabled_threshold_does_not_create_alert(
    client,
    test_session,
):
    _, sensor, _ = await create_sensor_and_threshold(
        test_session,
    )

    result = await test_session.execute(
        select(AlertThreshold).where(
            AlertThreshold.sensor_type == SensorType.PH,
            AlertThreshold.measurement_type == MeasurementType.PH,
        )
    )

    threshold = result.scalars().first()
    threshold.enabled = False

    await test_session.commit()

    response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": str(sensor.id),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "value_numeric": 5.5,
            "unit": "pH",
            "quality_status": ReadingQuality.GOOD.value,
            "source": ReadingSource.SIMULATOR.value,
        },
    )

    assert response.status_code == 201

    result = await test_session.execute(
        select(Alert).where(
            Alert.sensor_id == sensor.id,
        )
    )

    alerts = result.scalars().all()

    assert alerts == []


# ============================================================
# COOLDOWN THROUGH HTTP API
# ============================================================

@pytest.mark.asyncio
async def test_post_warning_readings_respect_alert_cooldown(
    client,
    test_session,
):
    _, sensor, _ = await create_sensor_and_threshold(
        test_session,
    )

    first_time = datetime.now(timezone.utc)

    first_response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": str(sensor.id),
            "recorded_at": first_time.isoformat(),
            "value_numeric": 6.3,
            "unit": "pH",
            "quality_status": ReadingQuality.GOOD.value,
            "source": ReadingSource.SIMULATOR.value,
        },
    )

    assert first_response.status_code == 201

    second_response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": str(sensor.id),
            "recorded_at": (
                first_time + timedelta(seconds=60)
            ).isoformat(),
            "value_numeric": 6.2,
            "unit": "pH",
            "quality_status": ReadingQuality.GOOD.value,
            "source": ReadingSource.SIMULATOR.value,
        },
    )

    assert second_response.status_code == 201

    result = await test_session.execute(
        select(Alert).where(
            Alert.sensor_id == sensor.id,
        )
    )

    alerts = result.scalars().all()

    assert len(alerts) == 1


# ============================================================
# COOLDOWN EXPIRATION THROUGH HTTP API
# ============================================================

@pytest.mark.asyncio
async def test_post_warning_reading_after_cooldown_creates_new_alert(
    client,
    test_session,
):
    _, sensor, _ = await create_sensor_and_threshold(
        test_session,
        )

    first_time = datetime.now(timezone.utc)

    first_response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": str(sensor.id),
            "recorded_at": first_time.isoformat(),
            "value_numeric": 6.3,
            "unit": "pH",
            "quality_status": ReadingQuality.GOOD.value,
            "source": ReadingSource.SIMULATOR.value,
        },
    )

    assert first_response.status_code == 201

    second_response = await client.post(
        "/api/v1/sensor-readings",
        json={
            "sensor_id": str(sensor.id),
            "recorded_at": (
                first_time + timedelta(seconds=901)
            ).isoformat(),
            "value_numeric": 6.2,
            "unit": "pH",
            "quality_status": ReadingQuality.GOOD.value,
            "source": ReadingSource.SIMULATOR.value,
        },
    )

    assert second_response.status_code == 201

    result = await test_session.execute(
        select(Alert).where(
            Alert.sensor_id == sensor.id,
        )
    )

    alerts = result.scalars().all()

    assert len(alerts) == 2