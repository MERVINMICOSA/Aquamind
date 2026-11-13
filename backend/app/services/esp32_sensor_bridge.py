"""Opt-in, fail-closed bridge from archived ESP32 packets to registered sensors.

The USB packet is the transport source; server receipt time is the observation
timestamp because the ESP32 v1 protocol has uptime, not an absolute clock.
No pump, relay, or actuator command may originate from this module.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from typing import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    CalibrationStatus,
    MeasurementType,
    ReadingQuality,
    ReadingSource,
    SensorType,
)
from app.models.sensors import Sensor, SensorCalibration, SensorReading
from app.schemas.esp32_telemetry import Esp32SensorPacket

logger = logging.getLogger(__name__)

# field -> (sensor type, measurement type, exact unit, optional raw diagnostic key)
# Do not register voltages, unverified estimates, or digital wet/dry flags as
# calibrated numeric sensor measurements.
FIELD_SPECS = {
    "water_temp_c": (SensorType.WATER_TEMPERATURE, MeasurementType.TEMPERATURE, "°C", "water_temperature"),
    "ph": (SensorType.PH, MeasurementType.PH, "pH", "ph"),
    "tds_ppm": (SensorType.TDS, MeasurementType.TDS, "ppm", "tds"),
    "water_level_pct": (SensorType.WATER_LEVEL, MeasurementType.LEVEL, "%", "ultrasonic"),
    "water_height_cm": (SensorType.WATER_LEVEL, MeasurementType.LEVEL, "cm", "ultrasonic"),
    "distance_cm": (SensorType.WATER_LEVEL, MeasurementType.LEVEL, "cm", "ultrasonic"),
    "air_temp_c": (SensorType.AIR_TEMPERATURE, MeasurementType.TEMPERATURE, "°C", "air_temperature"),
    "humidity_pct": (SensorType.HUMIDITY, MeasurementType.HUMIDITY, "%", "humidity"),
}


def parse_sensor_mapping(raw: str) -> dict[str, UUID]:
    """Validate explicit one-field-to-one-sensor bindings at startup.

    A nonempty map is required when this optional bridge is enabled. Mapping
    fields to multiple sensors, or unknown sensor fields, fails configuration.
    """
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("ESP32_SENSOR_MAP_JSON must contain valid JSON") from exc

    if not isinstance(parsed, dict) or not parsed:
        raise ValueError("ESP32_SENSOR_MAP_JSON must be a nonempty JSON object")

    result: dict[str, UUID] = {}
    for field, value in parsed.items():
        if field not in FIELD_SPECS:
            raise ValueError(f"Unsupported ESP32 sensor field: {field!r}")
        if not isinstance(value, str):
            raise ValueError("ESP32 sensor mappings must contain UUID strings")
        try:
            result[field] = UUID(value)
        except ValueError as exc:
            raise ValueError(f"Invalid sensor UUID configured for {field}") from exc

    if len(set(result.values())) != len(result):
        raise ValueError("Each ESP32 sensor field must map to a distinct sensor ID")
    return result


async def _verified_ph_tds_calibration(
    session: AsyncSession,
    *,
    sensor: Sensor,
    device_id: str,
) -> bool:
    """Require verified human-audited device calibration provenance.

    A claimed device calibration boolean and a database status alone do not
    validate a water-quality reading. Calibration metadata must record who
    verified that the active calibration was applied to THIS ESP32.
    """
    if sensor.calibration_status != CalibrationStatus.VERIFIED:
        return False

    result = await session.execute(
        select(SensorCalibration)
        .where(SensorCalibration.sensor_id == sensor.id)
        .order_by(
            SensorCalibration.performed_at.desc(),
            SensorCalibration.created_at.desc(),
            SensorCalibration.id.desc(),
        )
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if (
        latest is None
        or latest.status != CalibrationStatus.VERIFIED
        or latest.verified_by_user_id is None
        or not isinstance(latest.calibration_data, dict)
    ):
        return False
    data = latest.calibration_data
    return (
        data.get("esp32_device_id") == device_id
        and data.get("firmware_applied") is True
    )


async def build_sensor_readings(
    session: AsyncSession,
    *,
    system_id: UUID,
    packet: Esp32SensorPacket,
    sensor_mapping: Mapping[str, UUID],
    received_at: datetime,
) -> list[SensorReading]:
    """Build only trusted, configured numeric readings from one USB packet.

    Missing values, sensor mismatches, failed raw reads and unverified pH/TDS
    are excluded. The raw packet is still archived separately by the caller.
    """
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise ValueError("ESP32 received_at must be timezone-aware")

    results: list[SensorReading] = []
    for field, sensor_id in sensor_mapping.items():
        sensor = await session.get(Sensor, sensor_id)
        expected_type, expected_measurement, expected_unit, raw_key = FIELD_SPECS[field]
        expected_hardware_id = f"{packet.device_id}:{field}"
        if (
            sensor is None
            or sensor.system_id != system_id
            or sensor.deleted_at is not None
            or not sensor.is_enabled
            or sensor.is_simulated
            or sensor.hardware_identifier != expected_hardware_id
            or sensor.sensor_type != expected_type
            or sensor.measurement_type != expected_measurement
            or sensor.unit != expected_unit
        ):
            logger.warning("ESP32 bridge skipped %s: registered sensor configuration mismatch", field)
            continue

        value = getattr(packet, field)
        if value is None or not math.isfinite(value):
            continue

        # If firmware reported a failed sensor read, do not trust a stale or
        # contradictory top-level value in the same packet.
        raw = getattr(packet.raw_readings, raw_key, None) if packet.raw_readings else None
        if raw is not None and raw.status != "ok":
            logger.warning("ESP32 bridge skipped %s: firmware reported %s", field, raw.status)
            continue

        if field in ("ph", "tds_ppm"):
            device_claims_calibrated = (
                packet.ph_calibrated if field == "ph" else packet.tds_calibrated
            )
            if (
                not device_claims_calibrated
                or not await _verified_ph_tds_calibration(
                    session, sensor=sensor, device_id=packet.device_id,
                )
            ):
                logger.warning("ESP32 bridge skipped %s: verified device calibration required", field)
                continue

        results.append(SensorReading(
            sensor_id=sensor.id,
            recorded_at=received_at,
            value_numeric=value,
            unit=expected_unit,
            quality_status=ReadingQuality.GOOD,
            source=ReadingSource.HARDWARE,
            sequence_number=packet.sequence,
        ))

    return results
