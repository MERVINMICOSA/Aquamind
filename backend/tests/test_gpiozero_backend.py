from __future__ import annotations

import pytest

from app.hardware.driver import (
    HardwareActuatorDriverError,
)
from app.hardware import (
    gpiozero_backend,
)
from app.hardware.gpiozero_backend import (
    GPIOZeroBackend,
)


# ============================================================
# FAKE GPIO ZERO
# ============================================================


class FakeLGPIOFactory:
    instances = []

    def __init__(
        self,
        *,
        chip=None,
    ):
        self.chip = chip
        self.closed = False

        self.__class__.instances.append(
            self
        )

    def close(
        self,
    ):
        self.closed = True


class FakeOutputDevice:
    instances = []

    def __init__(
        self,
        pin,
        *,
        active_high,
        initial_value,
        pin_factory,
    ):
        self.pin = pin
        self.active_high = (
            active_high
        )
        self.pin_factory = (
            pin_factory
        )

        self.value = bool(
            initial_value
        )

        self.closed = False

        self.__class__.instances.append(
            self
        )

    def on(
        self,
    ):
        self.value = True

    def off(
        self,
    ):
        self.value = False

    def close(
        self,
    ):
        self.closed = True


# ============================================================
# FIXTURE
# ============================================================


@pytest.fixture(autouse=True)
def fake_gpiozero(
    monkeypatch,
):
    FakeLGPIOFactory.instances.clear()
    FakeOutputDevice.instances.clear()

    monkeypatch.setattr(
        gpiozero_backend,
        "_load_gpiozero_components",
        lambda: (
            FakeOutputDevice,
            FakeLGPIOFactory,
        ),
    )


# ============================================================
# CONFIGURATION
# ============================================================


def test_backend_requires_explicit_allowed_pins():
    with pytest.raises(
        ValueError,
        match=(
            "allowed_bcm_pins cannot be empty"
        ),
    ):
        GPIOZeroBackend(
            allowed_bcm_pins=set(),
        )


def test_invalid_allowed_pin_is_rejected():
    with pytest.raises(
        ValueError,
        match=(
            "between 0 and 27"
        ),
    ):
        GPIOZeroBackend(
            allowed_bcm_pins={
                17,
                40,
            },
        )


def test_invalid_gpio_chip_is_rejected():
    with pytest.raises(
        ValueError,
        match=(
            "GPIO chip must be a "
            "non-negative integer"
        ),
    ):
        GPIOZeroBackend(
            allowed_bcm_pins={
                17,
            },
            chip=-1,
        )


# ============================================================
# PIN ALLOWLIST
# ============================================================


def test_unapproved_pin_cannot_be_configured():
    backend = GPIOZeroBackend(
        allowed_bcm_pins={
            17,
        },
    )

    with pytest.raises(
        HardwareActuatorDriverError,
        match=(
            "BCM GPIO pin 18 is not allowed"
        ),
    ) as exc_info:
        backend.setup_output(
            18,
            initial_high=True,
        )

    assert (
        exc_info.value.fault_code
        == "gpio_pin_not_allowed"
    )

    # Rejection happens before the GPIO factory is opened.
    assert (
        FakeLGPIOFactory.instances
        == []
    )


# ============================================================
# GPIO FACTORY
# ============================================================


def test_configured_gpio_chip_is_used():
    backend = GPIOZeroBackend(
        allowed_bcm_pins={
            17,
        },
        chip=4,
    )

    backend.setup_output(
        17,
        initial_high=True,
    )

    assert (
        len(
            FakeLGPIOFactory.instances
        )
        == 1
    )

    assert (
        FakeLGPIOFactory
        .instances[0]
        .chip
        == 4
    )


# ============================================================
# OUTPUT INITIALIZATION
# ============================================================


def test_setup_output_preserves_explicit_initial_level():
    backend = GPIOZeroBackend(
        allowed_bcm_pins={
            17,
        },
    )

    backend.setup_output(
        17,
        initial_high=True,
    )

    assert (
        backend.read(17)
        is True
    )

    device = (
        FakeOutputDevice.instances[0]
    )

    assert (
        device.active_high
        is True
    )


def test_duplicate_output_setup_is_rejected():
    backend = GPIOZeroBackend(
        allowed_bcm_pins={
            17,
        },
    )

    backend.setup_output(
        17,
        initial_high=True,
    )

    with pytest.raises(
        HardwareActuatorDriverError,
        match=(
            "BCM GPIO pin 17 is "
            "already configured"
        ),
    ):
        backend.setup_output(
            17,
            initial_high=True,
        )


# ============================================================
# WRITE / READ
# ============================================================


def test_backend_writes_and_reads_raw_gpio_level():
    backend = GPIOZeroBackend(
        allowed_bcm_pins={
            17,
        },
    )

    backend.setup_output(
        17,
        initial_high=True,
    )

    assert (
        backend.read(17)
        is True
    )

    backend.write(
        17,
        high=False,
    )

    assert (
        backend.read(17)
        is False
    )

    backend.write(
        17,
        high=True,
    )

    assert (
        backend.read(17)
        is True
    )


def test_unconfigured_pin_cannot_be_written():
    backend = GPIOZeroBackend(
        allowed_bcm_pins={
            17,
        },
    )

    with pytest.raises(
        HardwareActuatorDriverError,
        match=(
            "BCM GPIO pin 17 is "
            "not configured"
        ),
    ) as exc_info:
        backend.write(
            17,
            high=True,
        )

    assert (
        exc_info.value.fault_code
        == "gpio_pin_not_configured"
    )


# ============================================================
# CLEANUP
# ============================================================


def test_cleanup_releases_devices_and_factory():
    backend = GPIOZeroBackend(
        allowed_bcm_pins={
            17,
            18,
        },
        chip=0,
    )

    backend.setup_output(
        17,
        initial_high=True,
    )

    backend.setup_output(
        18,
        initial_high=False,
    )

    devices = list(
        FakeOutputDevice.instances
    )

    factory = (
        FakeLGPIOFactory.instances[0]
    )

    backend.cleanup()

    assert all(
        device.closed
        for device in devices
    )

    assert factory.closed is True


def test_cleanup_is_idempotent():
    backend = GPIOZeroBackend(
        allowed_bcm_pins={
            17,
        },
    )

    backend.setup_output(
        17,
        initial_high=True,
    )

    backend.cleanup()

    # A second cleanup should safely do nothing.
    backend.cleanup()