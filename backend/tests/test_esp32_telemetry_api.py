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
