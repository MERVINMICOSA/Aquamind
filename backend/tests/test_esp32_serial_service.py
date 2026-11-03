from __future__ import annotations

import json
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.schemas.esp32_telemetry import Esp32SensorPacket
from app.services.esp32_serial_service import (
    Esp32SerialWorker,
    SerialJsonFramer,
    persist_esp32_packet,
)

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


def test_usb_json_parser_accepts_fragmented_compact_and_multiline_messages():
    framer = SerialJsonFramer()
    pretty = json.dumps(PACKET, indent=2).encode()
    single = json.dumps({**PACKET, "sequence": 6}).encode()
    data = b"ESP32 startup info\r\n" + pretty + b"\r\n" + single + b"\n"
    messages = []
    for offset in range(0, len(data), 17):
        messages.extend(framer.feed(data[offset:offset + 17]))
    assert len(messages) == 2
    assert messages[0] == PACKET
    assert messages[1]["sequence"] == 6


def test_usb_parser_rejects_oversized_payload_and_recovers():
    framer = SerialJsonFramer(max_bytes=200)
    assert framer.feed(b"{" + b" " * 300) == []
    # Framer has bounded memory and can read a subsequent small valid object.
    assert framer.feed(b'{"type":"aquamind_sensor"}\n') == [{"type": "aquamind_sensor"}]


def test_serial_port_must_be_explicit_linux_device(test_session_factory):
    with pytest.raises(ValueError):
        Esp32SerialWorker(
            test_session_factory,
            system_id=UUID(int=1),
            device_id=PACKET["device_id"],
            port="/etc/passwd",
        )


@pytest.mark.asyncio
async def test_usb_packet_saved_and_visible_to_dashboard(
    client: AsyncClient, test_session_factory,
):
    system = await client.post(
        "/api/v1/systems",
        json={"name": "USB ESP32", "timezone": "UTC", "is_active": True},
    )
    assert system.status_code == 201
    system_id = UUID(system.json()["id"])

    packet = Esp32SensorPacket.model_validate(PACKET)
    result = await persist_esp32_packet(
        test_session_factory, system_id=system_id,
        expected_device_id=PACKET["device_id"], packet=packet,
    )
    assert result == "created"

    same = await persist_esp32_packet(
        test_session_factory, system_id=system_id,
        expected_device_id=PACKET["device_id"], packet=packet,
    )
    assert same == "duplicate"

    conflicting = Esp32SensorPacket.model_validate({**PACKET, "humidity_pct": 77.0})
    assert await persist_esp32_packet(
        test_session_factory, system_id=system_id,
        expected_device_id=PACKET["device_id"], packet=conflicting,
    ) == "conflict"

    assert await persist_esp32_packet(
        test_session_factory, system_id=system_id,
        expected_device_id="another-device", packet=packet,
    ) == "conflict"

    latest = await client.get(
        "/api/v1/esp32/telemetry/latest", params={"system_id": str(system_id)},
    )
    assert latest.status_code == 200
    assert latest.json()["packet"] == {**PACKET, "raw_readings": None, "reservoir_water_present": None, "raft2_water_present": None}
    assert latest.json()["packet"]["ph"] is None
    assert latest.json()["packet"]["tds_ppm"] is None

    history = await client.get(
        "/api/v1/esp32/telemetry", params={"system_id": str(system_id)},
    )
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == latest.json()["id"]

    # USB-only: the previous HTTP POST ingestion surface is removed.
    post_response = await client.post("/api/v1/esp32/telemetry", json=PACKET)
    assert post_response.status_code == 405

    # Device packets do not trigger existing sensor automation/alerts.
    assert (await client.get("/api/v1/sensor-readings")).json() == []


@pytest.mark.asyncio
async def test_usb_raw_readings_survive_database_and_authenticated_api(
    client: AsyncClient, test_session_factory,
):
    system = await client.post(
        "/api/v1/systems",
        json={"name": "Raw readings", "timezone": "UTC", "is_active": True},
    )
    assert system.status_code == 201
    system_id = UUID(system.json()["id"])

    diagnostics = {
        "ph": {"status": "ok", "value": 0, "unit": "adc_count"},
        "tds": {"status": "ok", "value": 2076, "unit": "adc_count"},
        "ultrasonic": {
            "status": "timeout", "value": None,
            "unit": "microseconds", "error_code": "echo_timeout",
        },
        "water_temperature": {
            "status": "disconnected", "error_code": "ds18b20_disconnected",
        },
    }
    packet = Esp32SensorPacket.model_validate({
        **PACKET, "raw_readings": diagnostics,
    })
    assert await persist_esp32_packet(
        test_session_factory,
        system_id=system_id,
        expected_device_id=PACKET["device_id"],
        packet=packet,
    ) == "created"

    latest = await client.get(
        "/api/v1/esp32/telemetry/latest", params={"system_id": str(system_id)},
    )
    assert latest.status_code == 200
    assert latest.json()["packet"]["raw_readings"]["ph"]["value"] == 0
    assert latest.json()["packet"]["raw_readings"]["ultrasonic"]["status"] == "timeout"
    assert latest.json()["packet"]["raw_readings"]["water_temperature"]["error_code"] == "ds18b20_disconnected"
    assert latest.json()["packet"]["ph"] is None
    assert latest.json()["packet"]["tds_ppm"] is None


@pytest.mark.asyncio
async def test_missing_configured_parent_is_not_created_implicitly(
    test_session_factory,
):
    result = await persist_esp32_packet(
        test_session_factory,
        system_id=UUID(int=1),
        expected_device_id=PACKET["device_id"],
        packet=Esp32SensorPacket.model_validate(PACKET),
    )
    assert result == "unavailable"


@pytest.mark.asyncio
async def test_usb_worker_reads_packet_after_serial_reconnect(
    client: AsyncClient, test_session_factory,
):
    import asyncio
    import serial

    system = await client.post(
        "/api/v1/systems",
        json={"name": "USB reconnect test", "timezone": "UTC", "is_active": True},
    )
    assert system.status_code == 201
    system_id = UUID(system.json()["id"])

    class FakeUsbPort:
        def __init__(self):
            self.chunks = [
                b"ESP32 boot complete\\n",
                json.dumps(PACKET, indent=2).encode("utf-8"),
                b"\\n",
            ]
            self.closed = False

        def read(self, _size):
            return self.chunks.pop(0) if self.chunks else b""

        def close(self):
            self.closed = True

    port = FakeUsbPort()
    opens = []

    def open_usb(path, baudrate, timeout):
        assert path == "/dev/ttyACM0"
        assert baudrate == 115200
        assert timeout == 0.5
        opens.append(path)
        if len(opens) == 1:
            raise serial.SerialException("temporarily disconnected")
        return port

    worker = Esp32SerialWorker(
        test_session_factory,
        system_id=system_id,
        device_id=PACKET["device_id"],
        port="/dev/ttyACM0",
        serial_factory=open_usb,
        reconnect_seconds=0.01,
    )
    await worker.start()
    try:
        for _ in range(100):
            await asyncio.sleep(0.02)
            async with test_session_factory() as session:
                from sqlalchemy import select
                from app.models.esp32_telemetry import Esp32Telemetry

                records = (
                    await session.execute(select(Esp32Telemetry))
                ).scalars().all()
            if records:
                break
        assert len(records) == 1
        assert records[0].packet["water_temp_c"] == 27.56
        assert len(opens) == 2
    finally:
        await worker.stop()

    assert port.closed
