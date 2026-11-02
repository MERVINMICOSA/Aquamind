from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.db.enums import (
    ActuatorType,
)
from app.hardware.configuration import (
    HardwareConfigurationError,
    build_hardware_configuration,
)


# ============================================================
# SETTINGS HELPER
# ============================================================


def make_settings(
    *,
    enabled=True,
    gpio_chip="",
    allowed_pins="17,18",
    relay_channels=None,
):
    if relay_channels is None:
        relay_channels = [
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

    return SimpleNamespace(
        HARDWARE_ENABLED=enabled,
        HARDWARE_GPIO_CHIP=(
            gpio_chip
        ),
        HARDWARE_ALLOWED_BCM_PINS=(
            allowed_pins
        ),
        HARDWARE_RELAY_CHANNELS_JSON=(
            json.dumps(
                relay_channels
            )
        ),
    )


# ============================================================
# DISABLED MODE
# ============================================================


def test_disabled_hardware_requires_no_gpio_configuration():
    settings = SimpleNamespace(
        HARDWARE_ENABLED=False,
        HARDWARE_GPIO_CHIP="invalid",
        HARDWARE_ALLOWED_BCM_PINS=(
            "invalid"
        ),
        HARDWARE_RELAY_CHANNELS_JSON=(
            "{invalid"
        ),
    )

    config = (
        build_hardware_configuration(
            settings
        )
    )

    assert config.enabled is False

    assert config.gpio_chip is None

    assert (
        config.allowed_bcm_pins
        == frozenset()
    )

    assert (
        config.relay_channels
        == ()
    )


# ============================================================
# REQUIRED CONFIGURATION
# ============================================================


def test_enabled_hardware_requires_allowed_pins():
    settings = make_settings(
        allowed_pins="",
    )

    with pytest.raises(
        HardwareConfigurationError,
        match=(
            "HARDWARE_ALLOWED_BCM_PINS "
            "is empty"
        ),
    ):
        build_hardware_configuration(
            settings
        )


def test_enabled_hardware_requires_relay_channels():
    settings = make_settings(
        relay_channels=[],
    )

    with pytest.raises(
        HardwareConfigurationError,
        match=(
            "no relay channels are configured"
        ),
    ):
        build_hardware_configuration(
            settings
        )


# ============================================================
# VALID CONFIGURATION
# ============================================================


def test_valid_hardware_configuration_is_parsed():
    settings = make_settings(
        gpio_chip="4",
        allowed_pins="17,18",
        relay_channels=[
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
            {
                "identifier": (
                    "oxygen_pump"
                ),
                "actuator_type": (
                    "oxygen_pump"
                ),
                "bcm_pin": 18,
                "active_high": True,
            },
        ],
    )

    config = (
        build_hardware_configuration(
            settings
        )
    )

    assert config.enabled is True

    assert config.gpio_chip == 4

    assert (
        config.allowed_bcm_pins
        == frozenset(
            {
                17,
                18,
            }
        )
    )

    assert (
        len(
            config.relay_channels
        )
        == 2
    )

    assert (
        config.relay_channels[
            0
        ].identifier
        == "main_water_pump"
    )

    assert (
        config.relay_channels[
            0
        ].actuator_type
        == ActuatorType.WATER_PUMP
    )

    assert (
        config.relay_channels[
            0
        ].active_high
        is False
    )

    assert (
        config.relay_channels[
            1
        ].active_high
        is True
    )


# ============================================================
# PIN ALLOWLIST
# ============================================================


def test_relay_pin_must_be_in_allowlist():
    settings = make_settings(
        allowed_pins="18",
    )

    with pytest.raises(
        HardwareConfigurationError,
        match=(
            "main_water_pump uses BCM GPIO "
            "17, which is not in"
        ),
    ):
        build_hardware_configuration(
            settings
        )


# ============================================================
# DUPLICATE IDENTIFIER
# ============================================================


def test_duplicate_relay_identifier_is_rejected():
    settings = make_settings(
        relay_channels=[
            {
                "identifier": "pump",
                "actuator_type": (
                    "water_pump"
                ),
                "bcm_pin": 17,
            },
            {
                "identifier": "pump",
                "actuator_type": (
                    "oxygen_pump"
                ),
                "bcm_pin": 18,
            },
        ]
    )

    with pytest.raises(
        HardwareConfigurationError,
        match=(
            "Duplicate relay hardware identifier"
        ),
    ):
        build_hardware_configuration(
            settings
        )


# ============================================================
# DUPLICATE GPIO
# ============================================================


def test_duplicate_relay_gpio_pin_is_rejected():
    settings = make_settings(
        relay_channels=[
            {
                "identifier": "pump_a",
                "actuator_type": (
                    "water_pump"
                ),
                "bcm_pin": 17,
            },
            {
                "identifier": "pump_b",
                "actuator_type": (
                    "oxygen_pump"
                ),
                "bcm_pin": 17,
            },
        ]
    )

    with pytest.raises(
        HardwareConfigurationError,
        match=(
            "BCM GPIO pin 17 is already assigned"
        ),
    ):
        build_hardware_configuration(
            settings
        )


# ============================================================
# ACTUATOR TYPE
# ============================================================


def test_unknown_actuator_type_is_rejected():
    settings = make_settings(
        relay_channels=[
            {
                "identifier": "device",
                "actuator_type": (
                    "unsupported_device"
                ),
                "bcm_pin": 17,
            },
        ]
    )

    with pytest.raises(
        HardwareConfigurationError,
        match=(
            "Unsupported relay actuator type"
        ),
    ):
        build_hardware_configuration(
            settings
        )


# ============================================================
# POLARITY
# ============================================================


def test_invalid_relay_polarity_is_rejected():
    settings = make_settings(
        relay_channels=[
            {
                "identifier": "pump",
                "actuator_type": (
                    "water_pump"
                ),
                "bcm_pin": 17,
                "active_high": "false",
            },
        ]
    )

    with pytest.raises(
        HardwareConfigurationError,
        match=(
            "active_high must be a boolean"
        ),
    ):
        build_hardware_configuration(
            settings
        )


# ============================================================
# INVALID JSON
# ============================================================


def test_invalid_relay_json_is_rejected():
    settings = SimpleNamespace(
        HARDWARE_ENABLED=True,
        HARDWARE_GPIO_CHIP="",
        HARDWARE_ALLOWED_BCM_PINS=(
            "17"
        ),
        HARDWARE_RELAY_CHANNELS_JSON=(
            "{invalid"
        ),
    )

    with pytest.raises(
        HardwareConfigurationError,
        match=(
            "must contain valid JSON"
        ),
    ):
        build_hardware_configuration(
            settings
        )


# ============================================================
# GPIO CHIP
# ============================================================


def test_invalid_gpio_chip_is_rejected():
    settings = make_settings(
        gpio_chip="-1",
    )

    with pytest.raises(
        HardwareConfigurationError,
        match=(
            "HARDWARE_GPIO_CHIP must be "
            "a non-negative integer"
        ),
    ):
        build_hardware_configuration(
            settings
        )