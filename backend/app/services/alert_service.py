from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AlertSeverity, AlertStatus, ReadingQuality
from app.models.alerts import Alert, AlertThreshold
from app.models.sensors import Sensor, SensorReading
from app.services.alert_evaluator import evaluate_alert_severity


async def process_sensor_reading(
    session: AsyncSession,
    reading: SensorReading,
) -> Alert | None:
    """
    Evaluate a sensor reading and create an Alert when appropriate.

    Returns:
        Alert: newly created alert
        None: when no alert should be created
    """

    # ------------------------------------------------------------
    # 1. Only process usable readings
    # ------------------------------------------------------------

    if reading.quality_status != ReadingQuality.GOOD:
        return None

    # ------------------------------------------------------------
    # 2. Load sensor
    # ------------------------------------------------------------

    sensor = await session.get(
        Sensor,
        reading.sensor_id,
    )

    if sensor is None:
        return None

    # ------------------------------------------------------------
    # 3. Find matching enabled threshold
    # ------------------------------------------------------------

    result = await session.execute(
        select(AlertThreshold)
        .where(
            AlertThreshold.sensor_type == sensor.sensor_type,
            AlertThreshold.measurement_type == sensor.measurement_type,
            AlertThreshold.enabled.is_(True),
        )
        .order_by(AlertThreshold.updated_at.desc())
    )

    threshold = result.scalars().first()

    if threshold is None:
        return None

    # ------------------------------------------------------------
    # 4. Evaluate severity
    # ------------------------------------------------------------

    severity = evaluate_alert_severity(
        float(reading.value_numeric),
        warning_low=(
            float(threshold.warning_low)
            if threshold.warning_low is not None
            else None
        ),
        warning_high=(
            float(threshold.warning_high)
            if threshold.warning_high is not None
            else None
        ),
        critical_low=(
            float(threshold.critical_low)
            if threshold.critical_low is not None
            else None
        ),
        critical_high=(
            float(threshold.critical_high)
            if threshold.critical_high is not None
            else None
        ),
    )

    # ------------------------------------------------------------
    # 5. Normal reading
    # ------------------------------------------------------------

    if severity is None:
        return None

    # ------------------------------------------------------------
    # 6. Check cooldown
    # ------------------------------------------------------------

    cooldown_start = (
        reading.recorded_at
        - timedelta(seconds=threshold.cooldown_seconds)
    )

    existing_result = await session.execute(
        select(Alert)
        .where(
            Alert.sensor_id == sensor.id,
            Alert.threshold_id == threshold.id,
            Alert.status.in_(
                [
                    AlertStatus.ACTIVE,
                    AlertStatus.ACKNOWLEDGED,
                ]
            ),
            Alert.created_at >= cooldown_start,
        )
        .order_by(Alert.created_at.desc())
    )

    existing_alert = existing_result.scalars().first()

    if existing_alert is not None:
        return None

    # ------------------------------------------------------------
    # 7. Build alert message
    # ------------------------------------------------------------

    message = (
        f"{sensor.name} reported {reading.value_numeric} "
        f"{reading.unit} ({severity.value})"
    )

    # ------------------------------------------------------------
    # 8. Create alert
    # ------------------------------------------------------------

    alert = Alert(
        system_id=sensor.system_id,
        sensor_id=sensor.id,
        actuator_id=None,
        alert_type=sensor.measurement_type.value,
        severity=severity,
        message=message,
        trigger_value=reading.value_numeric,
        threshold_id=threshold.id,
        status=AlertStatus.ACTIVE,
        created_at=reading.recorded_at,
    )

    session.add(alert)

    await session.commit()
    await session.refresh(alert)

    return alert