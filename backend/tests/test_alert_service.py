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
from app.models.sensors import Sensor, SensorReading
from app.models.system import AquaponicsSystem
from app.services.alert_service import process_sensor_reading


# ============================================================
# TEST HELPERS
# ============================================================


async def create_system(session):
    system = AquaponicsSystem(
        name="Alert Service Test System",
    )

    session.add(system)
    await session.commit()
    await session.refresh(system)

    return system


async def create_sensor(
    session,
    system,
    *,
    sensor_type=SensorType.PH,
    measurement_type=MeasurementType.PH,
):
    sensor = Sensor(
        system_id=system.id,
        name="Test pH Sensor",
        sensor_type=sensor_type,
        measurement_type=measurement_type,
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
    updated_at=None,
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
        updated_at=updated_at or datetime.now(timezone.utc),
    )

    session.add(threshold)
    await session.commit()
    await session.refresh(threshold)

    return threshold


async def create_reading(
    session,
    sensor,
    *,
    value=7.0,
    recorded_at=None,
    quality_status=ReadingQuality.GOOD,
):
    reading = SensorReading(
        sensor_id=sensor.id,
        recorded_at=recorded_at or datetime.now(timezone.utc),
        value_numeric=value,
        unit="pH",
        quality_status=quality_status,
        source=ReadingSource.SIMULATOR,
    )

    session.add(reading)
    await session.commit()
    await session.refresh(reading)

    return reading


async def get_sensor_alerts(
    session,
    sensor,
):
    result = await session.execute(
        select(Alert)
        .where(Alert.sensor_id == sensor.id)
        .order_by(Alert.created_at)
    )

    return list(result.scalars().all())


# ============================================================
# THRESHOLD DISCOVERY
# ============================================================


@pytest.mark.asyncio
async def test_alert_service_uses_matching_sensor_threshold(
    test_session,
):
    system = await create_system(test_session)
    sensor = await create_sensor(
        test_session,
        system,
    )

    threshold = await create_threshold(
        test_session,
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=6.3,
    )

    alert = await process_sensor_reading(
        test_session,
        reading,
    )

    assert alert is not None
    assert alert.threshold_id == threshold.id
    assert alert.sensor_id == sensor.id


@pytest.mark.asyncio
async def test_no_matching_threshold_does_not_create_alert(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=5.0,
    )

    alert = await process_sensor_reading(
        test_session,
        reading,
    )

    alerts = await get_sensor_alerts(
        test_session,
        sensor,
    )

    assert alert is None
    assert alerts == []


# ============================================================
# DISABLED THRESHOLD
# ============================================================


@pytest.mark.asyncio
async def test_disabled_threshold_does_not_create_alert(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    await create_threshold(
        test_session,
        enabled=False,
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=5.5,
    )

    alert = await process_sensor_reading(
        test_session,
        reading,
    )

    alerts = await get_sensor_alerts(
        test_session,
        sensor,
    )

    assert alert is None
    assert alerts == []


# ============================================================
# NORMAL VALUE
# ============================================================


@pytest.mark.asyncio
async def test_normal_reading_does_not_create_alert(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    await create_threshold(
        test_session,
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=7.0,
    )

    alert = await process_sensor_reading(
        test_session,
        reading,
    )

    alerts = await get_sensor_alerts(
        test_session,
        sensor,
    )

    assert alert is None
    assert alerts == []


# ============================================================
# WARNING ALERT
# ============================================================


@pytest.mark.asyncio
async def test_warning_reading_creates_warning_alert(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    threshold = await create_threshold(
        test_session,
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=6.3,
    )

    alert = await process_sensor_reading(
        test_session,
        reading,
    )

    assert alert is not None
    assert alert.severity == AlertSeverity.WARNING
    assert alert.status == AlertStatus.ACTIVE
    assert alert.sensor_id == sensor.id
    assert alert.system_id == system.id
    assert alert.threshold_id == threshold.id
    assert float(alert.trigger_value) == 6.3


# ============================================================
# CRITICAL ALERT
# ============================================================


@pytest.mark.asyncio
async def test_critical_reading_creates_critical_alert(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    threshold = await create_threshold(
        test_session,
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=5.5,
    )

    alert = await process_sensor_reading(
        test_session,
        reading,
    )

    assert alert is not None
    assert alert.severity == AlertSeverity.CRITICAL
    assert alert.status == AlertStatus.ACTIVE
    assert alert.threshold_id == threshold.id
    assert float(alert.trigger_value) == 5.5


# ============================================================
# ALERT RELATIONSHIPS
# ============================================================


@pytest.mark.asyncio
async def test_created_alert_references_sensor_system_and_threshold(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    threshold = await create_threshold(
        test_session,
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=6.2,
    )

    alert = await process_sensor_reading(
        test_session,
        reading,
    )

    assert alert is not None
    assert alert.sensor_id == sensor.id
    assert alert.system_id == system.id
    assert alert.threshold_id == threshold.id
    assert alert.created_at == reading.recorded_at


# ============================================================
# BAD READING QUALITY
# ============================================================


@pytest.mark.asyncio
async def test_failed_reading_quality_does_not_create_alert(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    await create_threshold(
        test_session,
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=5.0,
        quality_status=ReadingQuality.FAIL,
    )

    alert = await process_sensor_reading(
        test_session,
        reading,
    )

    alerts = await get_sensor_alerts(
        test_session,
        sensor,
    )

    assert alert is None
    assert alerts == []


# ============================================================
# COOLDOWN
# ============================================================


@pytest.mark.asyncio
async def test_cooldown_prevents_duplicate_alerts(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    await create_threshold(
        test_session,
        cooldown_seconds=900,
    )

    first_time = datetime.now(timezone.utc)

    first_reading = await create_reading(
        test_session,
        sensor,
        value=6.2,
        recorded_at=first_time,
    )

    first_alert = await process_sensor_reading(
        test_session,
        first_reading,
    )

    second_reading = await create_reading(
        test_session,
        sensor,
        value=6.3,
        recorded_at=first_time + timedelta(seconds=60),
    )

    second_alert = await process_sensor_reading(
        test_session,
        second_reading,
    )

    alerts = await get_sensor_alerts(
        test_session,
        sensor,
    )

    assert first_alert is not None
    assert second_alert is None
    assert len(alerts) == 1


# ============================================================
# COOLDOWN EXPIRATION
# ============================================================


@pytest.mark.asyncio
async def test_alert_can_be_created_after_cooldown_expires(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    await create_threshold(
        test_session,
        cooldown_seconds=900,
    )

    first_time = datetime.now(timezone.utc)

    first_reading = await create_reading(
        test_session,
        sensor,
        value=6.2,
        recorded_at=first_time,
    )

    first_alert = await process_sensor_reading(
        test_session,
        first_reading,
    )

    second_reading = await create_reading(
        test_session,
        sensor,
        value=6.3,
        recorded_at=first_time + timedelta(seconds=901),
    )

    second_alert = await process_sensor_reading(
        test_session,
        second_reading,
    )

    alerts = await get_sensor_alerts(
        test_session,
        sensor,
    )

    assert first_alert is not None
    assert second_alert is not None
    assert len(alerts) == 2


# ============================================================
# MULTIPLE MATCHING THRESHOLDS
# ============================================================


@pytest.mark.asyncio
async def test_alert_service_uses_most_recent_matching_threshold(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    base_time = datetime.now(timezone.utc)

    older_threshold = await create_threshold(
        test_session,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
        updated_at=base_time,
    )

    newer_threshold = await create_threshold(
        test_session,
        warning_low=6.8,
        warning_high=7.2,
        critical_low=6.4,
        critical_high=7.6,
        updated_at=base_time + timedelta(seconds=1),
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=6.5,
        recorded_at=base_time + timedelta(seconds=2),
    )

    alert = await process_sensor_reading(
        test_session,
        reading,
    )

    assert older_threshold.id != newer_threshold.id
    assert alert is not None
    assert alert.threshold_id == newer_threshold.id
    assert alert.severity == AlertSeverity.WARNING


# ============================================================
# ACKNOWLEDGED ALERT COOLDOWN
# ============================================================


@pytest.mark.asyncio
async def test_acknowledged_alert_still_blocks_duplicate_during_cooldown(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    await create_threshold(
        test_session,
        cooldown_seconds=900,
    )

    first_time = datetime.now(timezone.utc)

    first_reading = await create_reading(
        test_session,
        sensor,
        value=6.2,
        recorded_at=first_time,
    )

    first_alert = await process_sensor_reading(
        test_session,
        first_reading,
    )

    assert first_alert is not None

    first_alert.status = AlertStatus.ACKNOWLEDGED

    await test_session.commit()
    await test_session.refresh(first_alert)

    second_reading = await create_reading(
        test_session,
        sensor,
        value=6.3,
        recorded_at=first_time + timedelta(seconds=60),
    )

    second_alert = await process_sensor_reading(
        test_session,
        second_reading,
    )

    alerts = await get_sensor_alerts(
        test_session,
        sensor,
    )

    assert second_alert is None
    assert len(alerts) == 1
    assert alerts[0].status == AlertStatus.ACKNOWLEDGED


# ============================================================
# RESOLVED ALERT COOLDOWN
# ============================================================


@pytest.mark.asyncio
async def test_resolved_alert_does_not_block_new_alert(
    test_session,
):
    system = await create_system(test_session)

    sensor = await create_sensor(
        test_session,
        system,
    )

    await create_threshold(
        test_session,
        cooldown_seconds=900,
    )

    first_time = datetime.now(timezone.utc)

    first_reading = await create_reading(
        test_session,
        sensor,
        value=6.2,
        recorded_at=first_time,
    )

    first_alert = await process_sensor_reading(
        test_session,
        first_reading,
    )

    assert first_alert is not None

    first_alert.status = AlertStatus.RESOLVED

    await test_session.commit()
    await test_session.refresh(first_alert)

    second_reading = await create_reading(
        test_session,
        sensor,
        value=6.3,
        recorded_at=first_time + timedelta(seconds=60),
    )

    second_alert = await process_sensor_reading(
        test_session,
        second_reading,
    )

    alerts = await get_sensor_alerts(
        test_session,
        sensor,
    )

    assert second_alert is not None
    assert len(alerts) == 2

    statuses = {
        alert.status
        for alert in alerts
    }

    assert AlertStatus.RESOLVED in statuses
    assert AlertStatus.ACTIVE in statuses

# ============================================================
# CALIBRATION-DEPENDENT ALERT SAFETY
# ============================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        CalibrationStatus.PENDING,
        CalibrationStatus.REJECTED,
        CalibrationStatus.EXPIRED,
    ],
)
async def test_unverified_ph_never_creates_threshold_alert(test_session, status):
    system = await create_system(test_session)
    sensor = await create_sensor(test_session, system)
    sensor.calibration_status = status
    await test_session.commit()

    await create_threshold(test_session)
    reading = await create_reading(test_session, sensor, value=5.0)

    assert await process_sensor_reading(test_session, reading) is None
    assert await get_sensor_alerts(test_session, sensor) == []


@pytest.mark.asyncio
async def test_disabled_sensor_does_not_create_threshold_alert(test_session):
    system = await create_system(test_session)
    sensor = await create_sensor(test_session, system)
    sensor.is_enabled = False
    await test_session.commit()

    await create_threshold(test_session)
    reading = await create_reading(test_session, sensor, value=5.0)

    assert await process_sensor_reading(test_session, reading) is None
    assert await get_sensor_alerts(test_session, sensor) == []


@pytest.mark.asyncio
async def test_unverified_tds_never_creates_threshold_alert(test_session):
    system = await create_system(test_session)
    sensor = await create_sensor(
        test_session,
        system,
        sensor_type=SensorType.TDS,
        measurement_type=MeasurementType.TDS,
    )
    sensor.calibration_status = CalibrationStatus.PENDING

    threshold = AlertThreshold(
        sensor_type=SensorType.TDS,
        measurement_type=MeasurementType.TDS,
        warning_low=100,
        warning_high=700,
        critical_low=50,
        critical_high=1000,
        cooldown_seconds=60,
        enabled=True,
        updated_at=datetime.now(timezone.utc),
    )
    test_session.add(threshold)
    await test_session.commit()

    reading = await create_reading(test_session, sensor, value=1500)
    assert await process_sensor_reading(test_session, reading) is None
    assert await get_sensor_alerts(test_session, sensor) == []


@pytest.mark.asyncio
async def test_verified_tds_still_generates_threshold_alert(test_session):
    system = await create_system(test_session)
    sensor = await create_sensor(
        test_session,
        system,
        sensor_type=SensorType.TDS,
        measurement_type=MeasurementType.TDS,
    )
    threshold = AlertThreshold(
        sensor_type=SensorType.TDS,
        measurement_type=MeasurementType.TDS,
        warning_low=100,
        warning_high=700,
        critical_low=50,
        critical_high=1000,
        cooldown_seconds=60,
        enabled=True,
        updated_at=datetime.now(timezone.utc),
    )
    test_session.add(threshold)
    await test_session.commit()

    reading = await create_reading(test_session, sensor, value=1500)
    alert = await process_sensor_reading(test_session, reading)
    assert alert is not None
    assert alert.severity == AlertSeverity.CRITICAL
