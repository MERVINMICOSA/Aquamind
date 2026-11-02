from __future__ import annotations

from uuid import uuid4

import pytest

from app.db.enums import (
    ActuatorCommandType,
    ActuatorType,
)
from app.hardware.driver import (
    HardwareActuatorDriverError,
)
from app.hardware.relay_driver import (
    RelayActuatorDriver,
    RelayChannelConfig,
    RelayHardwareRegistry,
)
from app.services.actuator_executor import (
    ActuatorExecutionCommand,
)


# ============================================================
# FAKE GPIO BACKEND
# ============================================================


class FakeGPIOBackend:
    def __init__(
        self,
    ):
        self.states = {}
        self.setup_calls = []
        self.write_calls = []
        self.cleaned = False

        self.force_read_value = None

    def setup_output(
        self,
        bcm_pin,
        *,
        initial_high,
    ):
        self.setup_calls.append(
            (
                bcm_pin,
                initial_high,
            )
        )

        self.states[
            bcm_pin
        ] = initial_high

    def write(
        self,
        bcm_pin,
        *,
        high,
    ):
        self.write_calls.append(
            (
                bcm_pin,
                high,
            )
        )

        self.states[
            bcm_pin
        ] = high

    def read(
        self,
        bcm_pin,
    ):
        if (
            self.force_read_value
            is not None
        ):
            return (
                self.force_read_value
            )

        return self.states[
            bcm_pin
        ]

    def cleanup(
        self,
    ):
        self.cleaned = True


# ============================================================
# HELPERS
# ============================================================


def create_registry(
    *,
    active_high=False,
):
    return RelayHardwareRegistry(
        [
            RelayChannelConfig(
                identifier=(
                    "main_water_pump"
                ),
                actuator_type=(
                    ActuatorType.WATER_PUMP
                ),
                bcm_pin=17,
                active_high=active_high,
            ),
        ]
    )


def create_command(
    *,
    command_type=(
        ActuatorCommandType.ACTIVATE
    ),
    actuator_type=(
        ActuatorType.WATER_PUMP
    ),
):
    return ActuatorExecutionCommand(
        actuator_id=uuid4(),
        actuator_type=actuator_type,
        hardware_identifier=(
            "main_water_pump"
        ),
        command_type=command_type,
        requested_value=1.0,
    )


# ============================================================
# REGISTRY SAFETY
# ============================================================


def test_registry_rejects_duplicate_identifiers():
    with pytest.raises(
        ValueError,
        match=(
            "Duplicate relay hardware identifier"
        ),
    ):
        RelayHardwareRegistry(
            [
                RelayChannelConfig(
                    identifier="pump",
                    actuator_type=(
                        ActuatorType.WATER_PUMP
                    ),
                    bcm_pin=17,
                ),
                RelayChannelConfig(
                    identifier="pump",
                    actuator_type=(
                        ActuatorType.OXYGEN_PUMP
                    ),
                    bcm_pin=18,
                ),
            ]
        )


def test_registry_rejects_duplicate_gpio_pins():
    with pytest.raises(
        ValueError,
        match=(
            "BCM GPIO pin 17 is already assigned"
        ),
    ):
        RelayHardwareRegistry(
            [
                RelayChannelConfig(
                    identifier="pump_a",
                    actuator_type=(
                        ActuatorType.WATER_PUMP
                    ),
                    bcm_pin=17,
                ),
                RelayChannelConfig(
                    identifier="pump_b",
                    actuator_type=(
                        ActuatorType.OXYGEN_PUMP
                    ),
                    bcm_pin=17,
                ),
            ]
        )


# ============================================================
# SAFE INITIALIZATION
# ============================================================


def test_active_low_relay_initializes_off():
    backend = FakeGPIOBackend()

    driver = RelayActuatorDriver(
        backend=backend,
        registry=create_registry(
            active_high=False
        ),
    )

    driver.initialize()

    # Active-low:
    # HIGH = OFF
    assert (
        backend.states[17]
        is True
    )


def test_active_high_relay_initializes_off():
    backend = FakeGPIOBackend()

    driver = RelayActuatorDriver(
        backend=backend,
        registry=create_registry(
            active_high=True
        ),
    )

    driver.initialize()

    # Active-high:
    # LOW = OFF
    assert (
        backend.states[17]
        is False
    )


# ============================================================
# EXECUTION
# ============================================================


def test_active_low_activate_sets_gpio_low():
    backend = FakeGPIOBackend()

    driver = RelayActuatorDriver(
        backend=backend,
        registry=create_registry(
            active_high=False
        ),
    )

    driver.initialize()

    result = driver.execute(
        create_command()
    )

    assert (
        backend.states[17]
        is False
    )

    assert (
        result.actual_value
        == 1.0
    )


def test_emergency_stop_always_sets_relay_off():
    backend = FakeGPIOBackend()

    driver = RelayActuatorDriver(
        backend=backend,
        registry=create_registry(
            active_high=False
        ),
    )

    driver.initialize()

    driver.execute(
        create_command(
            command_type=(
                ActuatorCommandType.ACTIVATE
            )
        )
    )

    assert (
        backend.states[17]
        is False
    )

    result = driver.execute(
        create_command(
            command_type=(
                ActuatorCommandType.EMERGENCY_STOP
            )
        )
    )

    assert (
        backend.states[17]
        is True
    )

    assert (
        result.actual_value
        == 0.0
    )


# ============================================================
# CONFIGURATION PROTECTION
# ============================================================


def test_actuator_type_mismatch_is_rejected():
    backend = FakeGPIOBackend()

    driver = RelayActuatorDriver(
        backend=backend,
        registry=create_registry(),
    )

    driver.initialize()

    with pytest.raises(
        HardwareActuatorDriverError,
        match=(
            "Actuator type does not match"
        ),
    ):
        driver.execute(
            create_command(
                actuator_type=(
                    ActuatorType.OXYGEN_PUMP
                )
            )
        )


def test_set_value_is_rejected_for_binary_relay():
    backend = FakeGPIOBackend()

    driver = RelayActuatorDriver(
        backend=backend,
        registry=create_registry(),
    )

    driver.initialize()

    with pytest.raises(
        HardwareActuatorDriverError,
        match=(
            "Relay driver does not support"
        ),
    ):
        driver.execute(
            create_command(
                command_type=(
                    ActuatorCommandType.SET_VALUE
                )
            )
        )


# ============================================================
# READBACK PROTECTION
# ============================================================


def test_gpio_readback_mismatch_fails_execution():
    backend = FakeGPIOBackend()

    driver = RelayActuatorDriver(
        backend=backend,
        registry=create_registry(
            active_high=False
        ),
    )

    driver.initialize()

    # ACTIVATE on an active-low relay expects LOW.
    # Force readback to HIGH.
    backend.force_read_value = True

    with pytest.raises(
        HardwareActuatorDriverError,
        match=(
            "GPIO output state did not match"
        ),
    ) as exc_info:
        driver.execute(
            create_command()
        )

    assert (
        exc_info.value.fault_code
        == "gpio_state_mismatch"
    )


# ============================================================
# SAFE SHUTDOWN
# ============================================================


def test_close_returns_relay_to_off_before_cleanup():
    backend = FakeGPIOBackend()

    driver = RelayActuatorDriver(
        backend=backend,
        registry=create_registry(
            active_high=False
        ),
    )

    driver.initialize()

    driver.execute(
        create_command()
    )

    assert (
        backend.states[17]
        is False
    )

    driver.close()

    # Active-low OFF = HIGH.
    assert (
        backend.states[17]
        is True
    )

    assert (
        backend.cleaned
        is True
    )