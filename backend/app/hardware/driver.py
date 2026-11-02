from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.actuator_executor import (
    ActuatorExecutionCommand,
)


# ============================================================
# HARDWARE ERRORS
# ============================================================


class HardwareActuatorDriverError(RuntimeError):
    """
    Expected hardware-level execution failure.

    Concrete Raspberry Pi drivers should raise this for
    recoverable hardware problems such as:

    - invalid hardware identifiers;
    - GPIO initialization failures;
    - unavailable output pins;
    - relay/device communication failures.

    Unexpected programming errors should not be converted into
    this exception automatically.
    """

    def __init__(
        self,
        message: str,
        *,
        fault_code: str = "hardware_driver_error",
    ) -> None:
        super().__init__(message)

        self.fault_code = fault_code


# ============================================================
# HARDWARE RESULT
# ============================================================


@dataclass(
    frozen=True,
    slots=True,
)
class HardwareDriverResult:
    """
    Confirmed result returned by the physical hardware driver.

    actual_value must represent what the driver can confirm,
    rather than merely repeating the requested value.
    """

    actual_value: float | None = None
    result_summary: str | None = None


# ============================================================
# HARDWARE DRIVER CONTRACT
# ============================================================


class HardwareActuatorDriver(Protocol):
    """
    Low-level hardware abstraction used by the Raspberry Pi
    ActuatorExecutor.

    Phase 9B will provide the concrete GPIO implementation.
    """

    def execute(
        self,
        command: ActuatorExecutionCommand,
    ) -> HardwareDriverResult:
        """
        Execute one physical actuator command.

        This method is intentionally synchronous because common
        Raspberry Pi GPIO libraries expose synchronous pin
        operations. The async executor runs it outside the event
        loop.
        """

        ...

    def close(self) -> None:
        """
        Release GPIO/device resources during application
        shutdown.
        """

        ...