from __future__ import annotations

import pytest

from app.core.config import settings
from app.schemas.esp32_telemetry import Esp32SensorPacket


PACKET = {
    "type": "aquamind_sensor",
    "schema_version": 1,
    "device_id": "esp32-devkit-01",
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


@pytest.mark.asyncio
async def test_v1_packet_persists_whole_record_and_supports_history(
    client, monkeypatch,
):
    system_response = await client.post(
        "/api/v1/systems",
        json={"name": "ESP32 Test", "description": None, "timezone": "UTC", "is_active": True},
    )
    assert system_response.status_code == 201
    system_id = system_response.json()["id"]

    monkeypatch.setattr(settings, "ESP32_INGEST_TOKEN", "t" * 48)
    monkeypatch.setattr(settings, "ESP32_DEVICE_ID", PACKET["device_id"])
    monkeypatch.setattr(settings, "ESP32_SYSTEM_ID", system_id)

    url = "/api/v1/esp32/telemetry"
    headers = {"X-ESP32-Token": "t" * 48}

    missing_token = await client.post(url, json=PACKET)
    assert missing_token.status_code == 401
    wrong_device = await client.post(
        url, json={**PACKET, "device_id": "attacker"}, headers=headers,
    )
    assert wrong_device.status_code == 403

    created = await client.post(url, json=PACKET, headers=headers)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["system_id"] == system_id
    assert item["packet"] == PACKET
    assert item["packet"]["ph"] is None
    assert item["packet"]["tds_ppm"] is None
    assert item["packet"]["ph_unverified_estimate"] == 17.45

    duplicate = await client.post(url, json=PACKET, headers=headers)
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == item["id"]

    conflict = await client.post(
        url, json={**PACKET, "humidity_pct": 50.0}, headers=headers,
    )
    assert conflict.status_code == 409

    history = await client.get(url, params={"system_id": system_id, "limit": 10})
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == item["id"]

    latest = await client.get(url + "/latest", params={"system_id": system_id})
    assert latest.status_code == 200
    assert latest.json()["id"] == item["id"]

    # Unverified values have not silently become production sensor readings.
    sensor_readings = await client.get("/api/v1/sensor-readings")
    assert sensor_readings.status_code == 200
    assert sensor_readings.json() == []


@pytest.mark.asyncio
async def test_esp32_requires_explicit_configuration(client, monkeypatch):
    monkeypatch.setattr(settings, "ESP32_INGEST_TOKEN", "")
    monkeypatch.setattr(settings, "ESP32_DEVICE_ID", "")
    monkeypatch.setattr(settings, "ESP32_SYSTEM_ID", "")
    response = await client.post(
        "/api/v1/esp32/telemetry",
        json=PACKET, headers={"X-ESP32-Token": "something"},
    )
    assert response.status_code == 503


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": 2},
        {"type": "other"},
        {"ph": 17.45, "ph_calibrated": False},
        {"tds_ppm": 1249, "tds_calibrated": False},
        {"ph": None, "ph_calibrated": True},
        {"tds_ppm": None, "tds_calibrated": True},
        {"humidity_pct": 120},
        {"water_level_pct": -1},
        {"ph": 17.45, "ph_calibrated": True},
    ],
)
def test_reject_invalid_or_untrusted_v1_values(changes):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Esp32SensorPacket.model_validate({**PACKET, **changes})


def test_accepts_genuinely_calibrated_readings():
    data = {**PACKET, "ph_calibrated": True, "ph": 7.1, "tds_calibrated": True, "tds_ppm": 900}
    assert Esp32SensorPacket.model_validate(data).ph == 7.1
