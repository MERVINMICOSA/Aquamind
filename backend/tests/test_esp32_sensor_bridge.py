"""End-to-end ESP32 USB archive -> registered sensor_readings integration.

All tests use an in-memory database and synthetic packets; no hardware or
external circulation pump is operated.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.enums import (
    AlertSeverity,
    CalibrationStatus,
    MeasurementType,
    ReadingQuality,
    ReadingSource,
    SensorType,
    UserRole,
)
from app.models.alerts import Alert, AlertThreshold
from app.models.esp32_telemetry import Esp32Telemetry
from app.models.sensors import SensorCalibration, SensorReading
from app.models.system import User
from app.schemas.esp32_telemetry import Esp32SensorPacket
from app.services.esp32_sensor_bridge import parse_sensor_mapping
from app.services.esp32_serial_service import persist_esp32_packet


DEVICE = "esp32-devkit-01"
PACKET = {
    "type": "aquamind_sensor",
    "schema_version": 1,
    "device_id": DEVICE,
    "sequence": 5,
    "uptime_ms": 15023,
    "water_temp_c": 27.56,
    "ph_voltage_v": 0.559,
    "ph_unverified_estimate": 17.45,
    "ph_calibrated": False,
    "ph": None,
    "tds_voltage_v": 2.435,
    "tds_unverified_ppm": 1249,
    "tds_calibrated": False,
    "tds_ppm": None,
    "distance_cm": None,
    "water_height_cm": None,
    "water_level_pct": None,
    "air_temp_c": 27.67,
    "humidity_pct": 84.60,
}


async def system_id(client):
    response = await client.post(
        "/api/v1/systems",
        json={"name": "ESP32 mapping system", "timezone": "UTC", "is_active": True},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


async def sensor_id(
    client, system, field, *, sensor_type, measurement_type, unit,
    hardware_identifier=None, is_simulated=False, is_enabled=True,
    calibration_status="pending",
):
    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": str(system),
            "name": f"ESP32 {field}",
            "sensor_type": sensor_type,
            "measurement_type": measurement_type,
            "location_type": "system",
            "unit": unit,
            "hardware_identifier": hardware_identifier or f"{DEVICE}:{field}",
            "is_simulated": is_simulated,
            "is_enabled": is_enabled,
            "sampling_interval_seconds": 30,
            "calibration_status": calibration_status,
        },
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


async def save(factory, system, mapping, packet=None):
    return await persist_esp32_packet(
        factory,
        system_id=system,
        expected_device_id=DEVICE,
        packet=Esp32SensorPacket.model_validate(packet or PACKET),
        sensor_mapping=mapping,
    )


async def readings(factory):
    async with factory() as session:
        return list((await session.execute(select(SensorReading))).scalars().all())


async def alerts(factory):
    async with factory() as session:
        return list((await session.execute(select(Alert))).scalars().all())


def test_bridge_mapping_rejects_unsafe_configuration():
    identifier = "12345678-1234-1234-1234-123456789abc"
    assert parse_sensor_mapping(json.dumps({"water_temp_c": identifier})) == {
        "water_temp_c": UUID(identifier)
    }
    invalid = [
        "", "[]", "{}", '{"unknown": "' + identifier + '"}',
        '{"ph_unverified_estimate": "' + identifier + '"}',
        '{"ph_voltage_v": "' + identifier + '"}',
        '{"water_temp_c": "not-a-uuid"}',
        '{"water_temp_c": 10}',
        json.dumps({"water_temp_c": identifier, "air_temp_c": identifier}),
    ]
    for raw in invalid:
        with pytest.raises(ValueError):
            parse_sensor_mapping(raw)


@pytest.mark.asyncio
async def test_mapped_temperature_reaches_sensor_history_exactly_once(
    client, test_session_factory,
):
    system = await system_id(client)
    sensor = await sensor_id(
        client, system, "water_temp_c",
        sensor_type="water_temperature", measurement_type="temperature", unit="°C",
    )
    binding = {"water_temp_c": sensor}
    assert await save(test_session_factory, system, binding) == "created"
    assert await save(test_session_factory, system, binding) == "duplicate"

    stored = await readings(test_session_factory)
    assert len(stored) == 1
    assert stored[0].sensor_id == sensor
    assert float(stored[0].value_numeric) == pytest.approx(27.56)
    assert stored[0].source == ReadingSource.HARDWARE
    assert stored[0].quality_status == ReadingQuality.GOOD
    assert stored[0].sequence_number == 5
    assert stored[0].recorded_at is not None

    latest = await client.get(
        "/api/v1/sensor-readings/latest", params={"system_id": str(system)},
    )
    assert latest.status_code == 200
    assert len(latest.json()) == 1
    assert latest.json()[0]["sensor_id"] == str(sensor)

    async with test_session_factory() as session:
        packets = list((await session.execute(select(Esp32Telemetry))).scalars().all())
    assert len(packets) == 1
    assert packets[0].packet["water_temp_c"] == 27.56


@pytest.mark.asyncio
async def test_multiple_fields_map_into_independent_registered_sensors(
    client, test_session_factory,
):
    system = await system_id(client)
    temp = await sensor_id(
        client, system, "water_temp_c",
        sensor_type="water_temperature", measurement_type="temperature", unit="°C",
    )
    humidity = await sensor_id(
        client, system, "humidity_pct",
        sensor_type="humidity", measurement_type="humidity", unit="%",
    )
    assert await save(
        test_session_factory, system,
        {"water_temp_c": temp, "humidity_pct": humidity},
    ) == "created"
    saved = await readings(test_session_factory)
    assert {r.sensor_id for r in saved} == {temp, humidity}
    assert {float(r.value_numeric) for r in saved} == {27.56, 84.6}


@pytest.mark.asyncio
async def test_missing_or_failed_field_does_not_create_fake_measurements(
    client, test_session_factory,
):
    system = await system_id(client)
    sensor = await sensor_id(
        client, system, "water_temp_c",
        sensor_type="water_temperature", measurement_type="temperature", unit="°C",
    )
    packet = {
        **PACKET,
        "water_temp_c": 27.56,
        "raw_readings": {
            "water_temperature": {
                "status": "disconnected", "value": None, "error_code": "ds18b20_missing",
            },
        },
    }
    assert await save(test_session_factory, system, {"water_temp_c": sensor}, packet) == "created"
    assert await readings(test_session_factory) == []
    assert (await client.get("/api/v1/esp32/telemetry", params={"system_id": str(system)})).json()


@pytest.mark.asyncio
@pytest.mark.parametrize("wrong", ["unit", "simulation", "disabled", "device", "system"])
async def test_untrusted_sensor_configuration_is_skipped_but_packet_archived(
    client, test_session_factory, wrong,
):
    system = await system_id(client)
    other_system = await system_id(client) if wrong == "system" else system
    sensor = await sensor_id(
        client, other_system, "water_temp_c",
        sensor_type="water_temperature", measurement_type="temperature",
        unit="C" if wrong == "unit" else "°C",
        hardware_identifier=f"{DEVICE}-wrong:water_temp_c" if wrong == "device" else None,
        is_simulated=(wrong == "simulation"),
        is_enabled=(wrong != "disabled"),
    )
    assert await save(test_session_factory, system, {"water_temp_c": sensor}) == "created"
    assert await readings(test_session_factory) == []
    async with test_session_factory() as session:
        assert len((await session.execute(select(Esp32Telemetry))).scalars().all()) == 1


async def set_calibration(session, sensor, *, device=DEVICE, verified=True, verified_by=True):
    user = User(
        username=f"auditor-{sensor}-{datetime.now(timezone.utc).timestamp()}",
        password_hash="test-hash", role=UserRole.ADMIN, is_active=True,
    )
    session.add(user)
    await session.flush()
    calibration = SensorCalibration(
        sensor_id=sensor,
        offset=0, factor=1,
        calibration_data={"esp32_device_id": device, "firmware_applied": True},
        performed_at=datetime.now(timezone.utc),
        status=CalibrationStatus.VERIFIED if verified else CalibrationStatus.REJECTED,
        verified_by_user_id=user.id if verified_by else None,
    )
    session.add(calibration)
    await session.commit()
    return calibration


@pytest.mark.asyncio
async def test_unverified_ph_is_not_upgraded_by_packet_boolean_or_estimate(
    client, test_session_factory,
):
    system = await system_id(client)
    sensor = await sensor_id(
        client, system, "ph", sensor_type="ph",
        measurement_type="ph", unit="pH",
        calibration_status="pending",
    )
    packet = {
        **PACKET,
        "ph_calibrated": True, "ph": 5.5,
    }
    assert await save(test_session_factory, system, {"ph": sensor}, packet) == "created"
    assert await readings(test_session_factory) == []


@pytest.mark.asyncio
async def test_verified_ph_requires_matching_audited_firmware_calibration(
    client, test_session_factory,
):
    system = await system_id(client)
    sensor = await sensor_id(
        client, system, "ph", sensor_type="ph",
        measurement_type="ph", unit="pH",
        calibration_status="verified",
    )
    packet = {**PACKET, "ph_calibrated": True, "ph": 5.5}
    async with test_session_factory() as session:
        await set_calibration(session, sensor, device="other-esp32")

    assert await save(test_session_factory, system, {"ph": sensor}, packet) == "created"
    assert await readings(test_session_factory) == []

    packet = {**packet, "sequence": 6, "uptime_ms": 18000}
    async with test_session_factory() as session:
        await set_calibration(session, sensor)

    assert await save(test_session_factory, system, {"ph": sensor}, packet) == "created"
    saved = await readings(test_session_factory)
    assert len(saved) == 1
    assert float(saved[0].value_numeric) == pytest.approx(5.5)


@pytest.mark.asyncio
async def test_verified_ph_alerts_are_created_atomically_and_cooldown_applies(
    client, test_session_factory,
):
    system = await system_id(client)
    sensor = await sensor_id(
        client, system, "ph", sensor_type="ph",
        measurement_type="ph", unit="pH",
        calibration_status="verified",
    )
    async with test_session_factory() as session:
        await set_calibration(session, sensor)
        session.add(AlertThreshold(
            sensor_type=SensorType.PH,
            measurement_type=MeasurementType.PH,
            warning_low=6.5,
            warning_high=7.5,
            critical_low=6.0,
            critical_high=8.0,
            cooldown_seconds=900,
            enabled=True,
            updated_at=datetime.now(timezone.utc),
        ))
        await session.commit()
    binding = {"ph": sensor}
    pkt = {**PACKET, "ph_calibrated": True, "ph": 5.5}
    assert await save(test_session_factory, system, binding, pkt) == "created"
    assert await save(test_session_factory, system, binding, pkt) == "duplicate"
    assert await save(test_session_factory, system, binding, {
        **pkt, "sequence": 6, "uptime_ms": 17000,
    }) == "created"
    assert len(await readings(test_session_factory)) == 2
    triggered = await alerts(test_session_factory)
    assert len(triggered) == 1
    assert triggered[0].sensor_id == sensor
    assert triggered[0].severity == AlertSeverity.CRITICAL


@pytest.mark.asyncio
async def test_conflicting_packet_identity_never_creates_extra_reading(
    client, test_session_factory,
):
    system = await system_id(client)
    sensor = await sensor_id(
        client, system, "water_temp_c",
        sensor_type="water_temperature", measurement_type="temperature", unit="°C",
    )
    mapping = {"water_temp_c": sensor}
    assert await save(test_session_factory, system, mapping) == "created"
    assert await save(test_session_factory, system, mapping, {
        **PACKET, "water_temp_c": 88.0,
    }) == "conflict"
    assert len(await readings(test_session_factory)) == 1


@pytest.mark.asyncio
async def test_ingestion_failure_rolls_back_packet_and_readings_together(
    client, test_session_factory, monkeypatch,
):
    import app.services.esp32_serial_service as serial_module

    system = await system_id(client)
    sensor = await sensor_id(
        client, system, "water_temp_c",
        sensor_type="water_temperature", measurement_type="temperature", unit="°C",
    )

    async def fail(*args, **kwargs):
        raise RuntimeError("simulated mapping failure")

    monkeypatch.setattr(serial_module, "build_sensor_readings", fail)
    with pytest.raises(RuntimeError, match="simulated mapping failure"):
        await save(test_session_factory, system, {"water_temp_c": sensor})
    assert await readings(test_session_factory) == []
    async with test_session_factory() as session:
        assert (await session.execute(select(Esp32Telemetry))).scalars().all() == []
