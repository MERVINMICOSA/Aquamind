from __future__ import annotations

import asyncio
from datetime import (
    datetime,
    timezone,
)

from app.db.enums import (
    ExecutionStatus,
)
from app.hardware.driver import (
    HardwareActuatorDriver,
    HardwareActuatorDriverError,
    HardwareDriverResult,
)
from app.services.actuator_executor import (
    ActuatorExecutionCommand,
    ActuatorExecutionResult,
)


# ============================================================
# RASPBERRY PI ACTUATOR EXECUTOR
# ============================================================


class RaspberryPiActuatorExecutor:
    """
    Hardware-neutral async executor around a Raspberry Pi
    hardware driver.

    This class deliberately contains no direct GPIO imports.

    Phase 9B provides the concrete driver while the Phase 8
    automation runtime continues depending only on the existing
    ActuatorExecutor protocol.
    """

    def __init__(
        self,
        *,
        driver: HardwareActuatorDriver,
    ) -> None:
        self._driver = driver

    async def execute(
        self,
        command: ActuatorExecutionCommand,
    ) -> ActuatorExecutionResult:
        """
        Dispatch one command to the physical hardware driver.

        Expected hardware failures become explicit FAILED
        execution results.

        Unexpected programming/runtime exceptions are allowed
        to propagate so the Phase 8 runtime can persist the
        executor failure rather than silently hiding a defect.
        """

        # ----------------------------------------------------
        # HARDWARE IDENTIFIER
        #
        # Phase 8 intentionally permits an actuator to exist
        # without physical hardware configuration.
        #
        # Phase 9 execution, however, cannot control a device
        # without an identifier.
        # ----------------------------------------------------

        hardware_identifier = (
            command.hardware_identifier
        )

        if (
            hardware_identifier is None
            or not hardware_identifier.strip()
        ):
            return ActuatorExecutionResult(
                status=ExecutionStatus.FAILED,
                completed_at=datetime.now(
                    timezone.utc
                ),
                actual_value=None,
                result_summary=(
                    "Hardware execution rejected"
                ),
                fault_code=(
                    "missing_hardware_identifier"
                ),
                error_message=(
                    "Actuator has no hardware identifier"
                ),
            )

        # ----------------------------------------------------
        # HARDWARE EXECUTION
        #
        # GPIO libraries are normally synchronous.
        #
        # Running the driver through asyncio.to_thread keeps
        # synchronous hardware access from blocking FastAPI's
        # event loop.
        # ----------------------------------------------------

        try:
            driver_result = await asyncio.to_thread(
                self._driver.execute,
                command,
            )

        except HardwareActuatorDriverError as exc:
            return ActuatorExecutionResult(
                status=ExecutionStatus.FAILED,
                completed_at=datetime.now(
                    timezone.utc
                ),
                actual_value=None,
                result_summary=(
                    "Hardware execution failed"
                ),
                fault_code=exc.fault_code,
                error_message=(
                    str(exc).strip()
                    or "Hardware actuator execution failed"
                ),
            )

        # ----------------------------------------------------
        # DRIVER CONTRACT
        #
        # A malformed driver result indicates a programming
        # error, not a recoverable device fault. Let the Phase
        # 8 runtime handle it through its executor-error path.
        # ----------------------------------------------------

        if not isinstance(
            driver_result,
            HardwareDriverResult,
        ):
            raise TypeError(
                "Hardware actuator driver returned "
                "an invalid result"
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return ActuatorExecutionResult(
            status=ExecutionStatus.COMPLETED,
            completed_at=datetime.now(
                timezone.utc
            ),
            actual_value=(
                driver_result.actual_value
            ),
            result_summary=(
                driver_result.result_summary
                or "Hardware execution completed"
            ),
            fault_code=None,
            error_message=None,
        )

    async def close(
        self,
    ) -> None:
        """
        Release physical hardware resources.

        Phase 9E will connect this to FastAPI application
        shutdown.
        """

        await asyncio.to_thread(
            self._driver.close
        )