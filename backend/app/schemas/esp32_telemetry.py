from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Esp32RawSensorReading(BaseModel):
    """Device-reported read outcome and sensor-native value, not a calibration."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    status: Literal["ok", "not_configured", "disconnected", "timeout", "read_error"]
    value: float | None = None
    unit: Literal[
        "adc_count", "microseconds", "celsius", "percent", "sensor_ticks", "volts"
    ] | None = None
    error_code: str | None = Field(
        default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"
    )

    @model_validator(mode="after")
    def raw_read_consistency(self) -> Self:
        if self.status == "ok" and self.value is None:
            raise ValueError("status=ok requires a real device-reported raw value")
        if self.status != "ok" and self.value is not None:
            raise ValueError("failed/unconfigured sensor reads cannot have a raw value")
        if self.value is not None and self.unit is None:
            raise ValueError("a raw value requires its unit")
        if self.value is not None and self.unit == "adc_count":
            if not self.value.is_integer() or not 0 <= self.value <= 65535:
                raise ValueError("raw ADC counts must be an integer between 0 and 65535")
        if self.value is not None and self.unit == "microseconds" and self.value < 0:
            raise ValueError("raw ultrasonic echo duration cannot be negative")
        return self


class Esp32RawReadings(BaseModel):
    """Optional per-sensor diagnostics; absent entries mean *not reported*."""

    model_config = ConfigDict(extra="forbid")

    water_temperature: Esp32RawSensorReading | None = None
    ph: Esp32RawSensorReading | None = None
    tds: Esp32RawSensorReading | None = None
    ultrasonic: Esp32RawSensorReading | None = None
    air_temperature: Esp32RawSensorReading | None = None
    humidity: Esp32RawSensorReading | None = None


class Esp32SensorPacket(BaseModel):
    """Firmware schema v1. Unverified estimates must never become calibrated values."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    type: Literal["aquamind_sensor"]
    schema_version: Literal[1]
    device_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")
    sequence: int = Field(ge=0, le=2147483647)
    uptime_ms: int = Field(ge=0, le=9223372036854775807)

    water_temp_c: float | None = Field(default=None, ge=-10, le=90)
    ph_voltage_v: float | None = Field(default=None, ge=0, le=5)
    ph_unverified_estimate: float | None = Field(default=None, ge=-1000, le=1000)
    ph_calibrated: bool
    ph: float | None = Field(default=None, ge=0, le=14)

    tds_voltage_v: float | None = Field(default=None, ge=0, le=5)
    tds_unverified_ppm: float | None = Field(default=None, ge=0, le=100000)
    tds_calibrated: bool
    tds_ppm: float | None = Field(default=None, ge=0, le=100000)

    distance_cm: float | None = Field(default=None, ge=0, le=100000)
    water_height_cm: float | None = Field(default=None, ge=0, le=100000)
    water_level_pct: float | None = Field(default=None, ge=0, le=100)
    air_temp_c: float | None = Field(default=None, ge=-50, le=90)
    humidity_pct: float | None = Field(default=None, ge=0, le=100)

    # Optional v1 extension: firmware must report these, never inferred from null.
    raw_readings: Esp32RawReadings | None = None

    @model_validator(mode="after")
    def calibration_consistency(self) -> Self:
        if self.ph_calibrated != (self.ph is not None):
            raise ValueError("ph requires ph_calibrated=true; uncalibrated ph must be null")
        if self.tds_calibrated != (self.tds_ppm is not None):
            raise ValueError("tds_ppm requires tds_calibrated=true; uncalibrated tds_ppm must be null")
        return self


class Esp32TelemetryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    received_at: datetime
    packet: Esp32SensorPacket
