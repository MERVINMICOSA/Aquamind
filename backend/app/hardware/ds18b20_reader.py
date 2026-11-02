from __future__ import annotations

import re
from collections.abc import Callable
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from app.hardware.sensor_reader import (
    HardwareSensorReading,
    HardwareSensorReadError,
)


# ============================================================
# CONSTANTS
# ============================================================


DEFAULT_W1_DEVICES_ROOT = Path(
    "/sys/bus/w1/devices"
)

DS18B20_IDENTIFIER_PATTERN = re.compile(
    r"^28-[0-9a-fA-F]{12}$"
)

TEMPERATURE_PATTERN = re.compile(
    r"\bt=(-?\d+)\b"
)

DS18B20_MIN_CELSIUS = -55.0
DS18B20_MAX_CELSIUS = 125.0


# ============================================================
# CLOCK
# ============================================================


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


# ============================================================
# DS18B20 READER
# ============================================================


class DS18B20Reader:
    """
    Read a DS18B20 through Linux's 1-Wire sysfs interface.

    Expected device structure:

        /sys/bus/w1/devices/
            28-xxxxxxxxxxxx/
                w1_slave

    No Raspberry Pi dependency is imported directly here.
    This allows the parser/reader to be fully tested on Windows
    by providing another filesystem root.
    """

    def __init__(
        self,
        *,
        devices_root: str | Path = (
            DEFAULT_W1_DEVICES_ROOT
        ),
        clock: Callable[
            [],
            datetime,
        ] = _utc_now,
    ) -> None:
        self._devices_root = Path(
            devices_root
        )

        self._clock = clock

    # ========================================================
    # IDENTIFIER
    # ========================================================

    @staticmethod
    def supports_identifier(
        hardware_identifier: str,
    ) -> bool:
        """
        Return True when the identifier has the DS18B20
        1-Wire ROM-ID format handled by this adapter.

        This identifies HOW the physical device is read.
        It does not decide whether the sensor represents
        water temperature or air temperature.
        """

        if not isinstance(
            hardware_identifier,
            str,
        ):
            return False

        identifier = (
            hardware_identifier
            .strip()
        )

        return (
            DS18B20_IDENTIFIER_PATTERN
            .fullmatch(
                identifier
            )
            is not None
        )

    @staticmethod
    def _normalize_identifier(
        hardware_identifier: str,
    ) -> str:
        identifier = (
            hardware_identifier
            .strip()
            .lower()
        )

        if not (
            DS18B20_IDENTIFIER_PATTERN
            .fullmatch(
                identifier
            )
        ):
            raise HardwareSensorReadError(
                "Invalid DS18B20 hardware identifier",
                fault_code=(
                    "invalid_hardware_identifier"
                ),
            )

        return identifier

    # ========================================================
    # PAYLOAD PARSING
    # ========================================================

    @staticmethod
    def _parse_temperature(
        payload: str,
    ) -> float:
        lines = payload.splitlines()

        if len(lines) < 2:
            raise HardwareSensorReadError(
                "DS18B20 payload is incomplete",
                fault_code=(
                    "sensor_payload_invalid"
                ),
            )

        # ----------------------------------------------------
        # CRC / DEVICE VALIDITY
        # ----------------------------------------------------

        if not (
            lines[0]
            .strip()
            .endswith("YES")
        ):
            raise HardwareSensorReadError(
                "DS18B20 CRC validation failed",
                fault_code=(
                    "sensor_crc_invalid"
                ),
            )

        # ----------------------------------------------------
        # TEMPERATURE
        #
        # Linux 1-Wire reports t= in thousandths of one degree
        # Celsius.
        # ----------------------------------------------------

        match = None

        for line in lines[1:]:
            match = TEMPERATURE_PATTERN.search(
                line
            )

            if match is not None:
                break

        if match is None:
            raise HardwareSensorReadError(
                "DS18B20 temperature value is missing",
                fault_code=(
                    "sensor_payload_invalid"
                ),
            )

        try:
            raw_temperature = int(
                match.group(1)
            )

        except ValueError as exc:
            raise HardwareSensorReadError(
                "DS18B20 temperature value is invalid",
                fault_code=(
                    "sensor_payload_invalid"
                ),
            ) from exc

        temperature_celsius = (
            raw_temperature
            / 1000.0
        )

        # ----------------------------------------------------
        # PHYSICAL SENSOR RANGE
        #
        # Reject values outside the DS18B20's supported
        # measurement range rather than allowing obviously
        # corrupt data into AquaMind.
        # ----------------------------------------------------

        if (
            temperature_celsius
            < DS18B20_MIN_CELSIUS
            or temperature_celsius
            > DS18B20_MAX_CELSIUS
        ):
            raise HardwareSensorReadError(
                "DS18B20 temperature is outside "
                "the supported measurement range",
                fault_code=(
                    "sensor_value_out_of_range"
                ),
            )

        return temperature_celsius

    # ========================================================
    # READ
    # ========================================================

    def read(
        self,
        hardware_identifier: str,
    ) -> HardwareSensorReading:
        """
        Read one specific DS18B20.

        The exact hardware identifier will eventually come from
        Sensor.hardware_identifier.
        """

        identifier = (
            self._normalize_identifier(
                hardware_identifier
            )
        )

        data_file = (
            self._devices_root
            / identifier
            / "w1_slave"
        )

        # ----------------------------------------------------
        # DEVICE PRESENCE
        # ----------------------------------------------------

        if not data_file.is_file():
            raise HardwareSensorReadError(
                "DS18B20 sensor was not found",
                fault_code=(
                    "sensor_not_found"
                ),
            )

        # ----------------------------------------------------
        # FILESYSTEM READ
        # ----------------------------------------------------

        try:
            payload = data_file.read_text(
                encoding="utf-8"
            )

        except OSError as exc:
            raise HardwareSensorReadError(
                "Failed to read DS18B20 sensor",
                fault_code=(
                    "sensor_read_failed"
                ),
            ) from exc

        # ----------------------------------------------------
        # PARSE
        # ----------------------------------------------------

        temperature = (
            self._parse_temperature(
                payload
            )
        )

        recorded_at = self._clock()

        if (
            recorded_at.tzinfo is None
            or recorded_at.utcoffset()
            is None
        ):
            raise HardwareSensorReadError(
                "Sensor reader clock must return "
                "a timezone-aware datetime",
                fault_code=(
                    "invalid_sensor_timestamp"
                ),
            )

        return HardwareSensorReading(
            hardware_identifier=(
                identifier
            ),
            value_numeric=temperature,
            recorded_at=recorded_at,
        )