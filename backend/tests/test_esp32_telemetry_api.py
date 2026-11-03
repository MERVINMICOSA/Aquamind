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


def test_accepts_device_raw_readings_and_distinguishes_zero_from_null():
    packet = Esp32SensorPacket.model_validate({
        **PACKET,
        "raw_readings": {
            "ph": {"status": "ok", "value": 0, "unit": "adc_count"},
            "tds": {"status": "ok", "value": 2145, "unit": "adc_count"},
            "ultrasonic": {
                "status": "timeout", "unit": "microseconds",
                "error_code": "echo_timeout",
            },
            "water_temperature": {"status": "not_configured"},
        },
    })
    assert packet.raw_readings.ph.value == 0
    assert packet.raw_readings.ultrasonic.value is None
    assert packet.raw_readings.water_temperature.status == "not_configured"
    assert packet.ph is None  # pH is uncalibrated, *not* necessarily broken


@pytest.mark.parametrize(
    "bad_reading",
    [
        {"status": "ok", "value": None, "unit": "adc_count"},
        {"status": "ok", "value": 20},
        {"status": "read_error", "value": 123, "unit": "adc_count"},
        {"status": "ok", "value": 70000, "unit": "adc_count"},
        {"status": "ok", "value": 0.5, "unit": "adc_count"},
        {"status": "ok", "value": -10, "unit": "microseconds"},
        {"status": "unknown", "value": 20, "unit": "adc_count"},
        {"status": "ok", "value": float("nan"), "unit": "volts"},
    ],
)
def test_reject_invalid_or_misleading_raw_diagnostics(bad_reading):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Esp32SensorPacket.model_validate({
            **PACKET, "raw_readings": {"ph": bad_reading},
        })


def test_legacy_packets_do_not_fabricate_raw_readings_when_persisted():
    packet = Esp32SensorPacket.model_validate(PACKET)
    assert packet.raw_readings is None
    assert "raw_readings" not in packet.model_dump(mode="json", exclude_unset=True)


def test_two_red_presence_probes_keep_raw_adc_separate_from_wet_dry():
    packet = Esp32SensorPacket.model_validate({
        **PACKET,
        "reservoir_water_present": None,
        "raft2_water_present": None,
        "raw_readings": {
            "reservoir_level": {"status": "ok", "value": 0, "unit": "adc_count"},
            "raft2_level": {"status": "ok", "value": 1760, "unit": "adc_count"},
        },
    })
    assert packet.raw_readings.reservoir_level.value == 0
    assert packet.raw_readings.raft2_level.value == 1760
    assert packet.reservoir_water_present is None
    assert packet.raft2_water_present is None
    packet2 = Esp32SensorPacket.model_validate({
        **PACKET,
        "reservoir_water_present": False,
        "raft2_water_present": True,
    })
    assert packet2.reservoir_water_present is False
    assert packet2.raft2_water_present is True
