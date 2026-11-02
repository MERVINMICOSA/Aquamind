from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


# ============================================================
# SENSOR HARDWARE ERRORS
# ============================================================


class HardwareSensorReadError(RuntimeError):
    """
    Expected failure while reading a physical sensor.

    fault_code provides a stable machine-readable reason while
    the exception message remains useful for logs/operators.
    """

    def __init__(
        self,
        message: str,
        *,
        fault_code: str = "sensor_read_error",
    ) -> None:
        super().__init__(message)

        self.fault_code = fault_code


# ============================================================
# SENSOR READING
# ============================================================


@dataclass(
    frozen=True,
    slots=True,
)
class HardwareSensorReading:
    """
    Hardware-neutral numeric sensor reading.

    Unit/measurement metadata remains owned by AquaMind's
    Sensor model rather than being duplicated in every hardware
    adapter.
    """

    hardware_identifier: str
    value_numeric: float
    recorded_at: datetime


# ============================================================
# SENSOR READER CONTRACT
# ============================================================


class HardwareSensorReader(Protocol):
    """
    Contract implemented by physical sensor adapters.

    Examples:

        DS18B20Reader
        future pH adapter
        future TDS adapter
        future water-level adapter
    """

    def read(
        self,
        hardware_identifier: str,
    ) -> HardwareSensorReading:
        ...