from __future__ import annotations

from uuid import uuid4

import pytest

from app.db.enums import (
    ActuatorCommandType,
    ActuatorType,
    ExecutionStatus,
)
from app.hardware.driver import (
    HardwareActuatorDriverError,
    HardwareDriverResult,
)
from app.hardware.raspberry_pi_executor import (
    RaspberryPiActuatorExecutor,
)
from app.services.actuator_executor import (
    ActuatorExecutionCommand,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# TEST DRIVERS
# ============================================================


class SuccessfulDriver:
    def __init__(self):
        self.commands = []
        self.closed = False

    def execute(
        self,
        command,
    ):
        self.commands.append(
            command
        )

        return HardwareDriverResult(
            actual_value=1.0,
            result_summary=(
                "Relay output confirmed"
            ),
        )

    def close(
        self,
    ):
        self.closed = True


class FailingHardwareDriver:
    def execute(
        self,
        command,
    ):
        raise HardwareActuatorDriverError(
            "GPIO output unavailable",
            fault_code="gpio_unavailable",
        )

    def close(
        self,
    ):
        pass


class UnexpectedFailureDriver:
    def execute(
        self,
        command,
    ):
        raise RuntimeError(
            "Unexpected driver programming failure"
        )

    def close(
        self,
    ):
        pass


class InvalidResultDriver:
    def execute(
        self,
        command,
    ):
        return "invalid"

    def close(
        self,
    ):
        pass


# ============================================================
# HELPERS
# ============================================================


def make_command(
    *,
    hardware_identifier="gpio:17",
):
    return ActuatorExecutionCommand(
        actuator_id=uuid4(),
        actuator_type=(
            ActuatorType.WATER_PUMP
        ),
        hardware_identifier=(
            hardware_identifier
        ),
        command_type=(
            ActuatorCommandType.ACTIVATE
        ),
        requested_value=1.0,
    )


# ============================================================
# SUCCESS
# ============================================================


async def test_successful_hardware_execution_returns_completed():
    driver = SuccessfulDriver()

    executor = RaspberryPiActuatorExecutor(
        driver=driver
    )

    command = make_command()

    result = await executor.execute(
        command
    )

    assert (
        result.status
        == ExecutionStatus.COMPLETED
    )

    assert result.actual_value == 1.0

    assert (
        result.result_summary
        == "Relay output confirmed"
    )

    assert result.fault_code is None
    assert result.error_message is None

    assert driver.commands == [
        command
    ]

    assert (
        result.completed_at.tzinfo
        is not None
    )


# ============================================================
# HARDWARE IDENTIFIER
# ============================================================


async def test_missing_hardware_identifier_fails_without_driver_call():
    driver = SuccessfulDriver()

    executor = RaspberryPiActuatorExecutor(
        driver=driver
    )

    command = make_command(
        hardware_identifier=None
    )

    result = await executor.execute(
        command
    )

    assert (
        result.status
        == ExecutionStatus.FAILED
    )

    assert (
        result.fault_code
        == "missing_hardware_identifier"
    )

    assert driver.commands == []


# ============================================================
# EXPECTED HARDWARE FAILURE
# ============================================================


async def test_expected_hardware_error_returns_failed_result():
    executor = RaspberryPiActuatorExecutor(
        driver=FailingHardwareDriver()
    )

    result = await executor.execute(
        make_command()
    )

    assert (
        result.status
        == ExecutionStatus.FAILED
    )

    assert (
        result.fault_code
        == "gpio_unavailable"
    )

    assert (
        result.error_message
        == "GPIO output unavailable"
    )


# ============================================================
# UNEXPECTED DRIVER FAILURE
# ============================================================


async def test_unexpected_driver_exception_is_not_hidden():
    executor = RaspberryPiActuatorExecutor(
        driver=UnexpectedFailureDriver()
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Unexpected driver programming failure"
        ),
    ):
        await executor.execute(
            make_command()
        )


# ============================================================
# MALFORMED DRIVER RESULT
# ============================================================


async def test_invalid_driver_result_is_rejected():
    executor = RaspberryPiActuatorExecutor(
        driver=InvalidResultDriver()
    )

    with pytest.raises(
        TypeError,
        match=(
            "Hardware actuator driver returned "
            "an invalid result"
        ),
    ):
        await executor.execute(
            make_command()
        )


# ============================================================
# SHUTDOWN
# ============================================================


async def test_executor_close_releases_driver_resources():
    driver = SuccessfulDriver()

    executor = RaspberryPiActuatorExecutor(
        driver=driver
    )

    assert driver.closed is False

    await executor.close()

    assert driver.closed is True