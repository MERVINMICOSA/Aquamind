from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.hardware import runtime as hardware_runtime


pytestmark = pytest.mark.asyncio


# ============================================================
# SETTINGS
# ============================================================


def make_settings(
    *,
    enabled=True,
):
    return SimpleNamespace(
        HARDWARE_ENABLED=enabled,
        HARDWARE_GPIO_CHIP="0",
        HARDWARE_ALLOWED_BCM_PINS=(
            "17,18"
        ),
        HARDWARE_RELAY_CHANNELS_JSON=(
            json.dumps(
                [
                    {
                        "identifier": (
                            "main_water_pump"
                        ),
                        "actuator_type": (
                            "water_pump"
                        ),
                        "bcm_pin": 17,
                        "active_high": False,
                    },
                ]
            )
        ),
    )


# ============================================================
# DISABLED HARDWARE
# ============================================================


async def test_disabled_hardware_returns_none_without_gpio(
    monkeypatch,
):
    class GPIOConstructionMustNotOccur:
        def __init__(
            self,
            *args,
            **kwargs,
        ):
            raise AssertionError(
                "GPIO must not initialize when "
                "hardware is disabled"
            )

    monkeypatch.setattr(
        hardware_runtime,
        "GPIOZeroBackend",
        GPIOConstructionMustNotOccur,
    )

    executor = (
        await hardware_runtime
        .build_hardware_actuator_executor(
            make_settings(
                enabled=False
            )
        )
    )

    assert executor is None


# ============================================================
# ENABLED HARDWARE COMPOSITION
# ============================================================


async def test_enabled_hardware_builds_and_initializes_stack(
    monkeypatch,
):
    created = {}

    class FakeBackend:
        def __init__(
            self,
            *,
            allowed_bcm_pins,
            chip,
        ):
            self.allowed_bcm_pins = (
                allowed_bcm_pins
            )

            self.chip = chip

            created["backend"] = self

    class FakeDriver:
        def __init__(
            self,
            *,
            backend,
            registry,
        ):
            self.backend = backend
            self.registry = registry

            self.initialized = False
            self.closed = False

            created["driver"] = self

        def initialize(
            self,
        ):
            self.initialized = True

        def close(
            self,
        ):
            self.closed = True

    class FakeExecutor:
        def __init__(
            self,
            *,
            driver,
        ):
            self.driver = driver
            self.closed = False

            created["executor"] = self

        async def close(
            self,
        ):
            self.closed = True
            self.driver.close()

    monkeypatch.setattr(
        hardware_runtime,
        "GPIOZeroBackend",
        FakeBackend,
    )

    monkeypatch.setattr(
        hardware_runtime,
        "RelayActuatorDriver",
        FakeDriver,
    )

    monkeypatch.setattr(
        hardware_runtime,
        "RaspberryPiActuatorExecutor",
        FakeExecutor,
    )

    executor = (
        await hardware_runtime
        .build_hardware_actuator_executor(
            make_settings()
        )
    )

    backend = created[
        "backend"
    ]

    driver = created[
        "driver"
    ]

    assert (
        backend.allowed_bcm_pins
        == frozenset(
            {
                17,
                18,
            }
        )
    )

    assert backend.chip == 0

    assert driver.initialized is True

    assert executor is created[
        "executor"
    ]


# ============================================================
# INITIALIZATION FAILURE
# ============================================================


async def test_hardware_initialization_failure_propagates(
    monkeypatch,
):
    executor_created = False

    class FakeBackend:
        def __init__(
            self,
            *,
            allowed_bcm_pins,
            chip,
        ):
            pass

    class FailingDriver:
        def __init__(
            self,
            *,
            backend,
            registry,
        ):
            pass

        def initialize(
            self,
        ):
            raise RuntimeError(
                "GPIO initialization failed"
            )

        def close(
            self,
        ):
            pass

    class ExecutorMustNotBeCreated:
        def __init__(
            self,
            *,
            driver,
        ):
            nonlocal executor_created

            executor_created = True

    monkeypatch.setattr(
        hardware_runtime,
        "GPIOZeroBackend",
        FakeBackend,
    )

    monkeypatch.setattr(
        hardware_runtime,
        "RelayActuatorDriver",
        FailingDriver,
    )

    monkeypatch.setattr(
        hardware_runtime,
        "RaspberryPiActuatorExecutor",
        ExecutorMustNotBeCreated,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "GPIO initialization failed"
        ),
    ):
        await (
            hardware_runtime
            .build_hardware_actuator_executor(
                make_settings()
            )
        )

    assert executor_created is False


# ============================================================
# SHUTDOWN
# ============================================================


async def test_shutdown_closes_executor():
    class FakeExecutor:
        def __init__(
            self,
        ):
            self.closed = False

        async def close(
            self,
        ):
            self.closed = True

    executor = FakeExecutor()

    await (
        hardware_runtime
        .shutdown_hardware_actuator_executor(
            executor
        )
    )

    assert executor.closed is True


async def test_shutdown_without_executor_is_safe():
    await (
        hardware_runtime
        .shutdown_hardware_actuator_executor(
            None
        )
    )