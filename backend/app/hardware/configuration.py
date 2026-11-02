from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from app.db.enums import (
    ActuatorType,
)
from app.hardware.relay_driver import (
    RelayChannelConfig,
    RelayHardwareRegistry,
)


# ============================================================
# EXCEPTIONS
# ============================================================


class HardwareConfigurationError(
    ValueError
):
    """
    Raised when AquaMind hardware deployment configuration
    is invalid.
    """


# ============================================================
# SETTINGS CONTRACT
# ============================================================


class HardwareSettings(Protocol):
    HARDWARE_ENABLED: bool
    HARDWARE_GPIO_CHIP: str
    HARDWARE_ALLOWED_BCM_PINS: str
    HARDWARE_RELAY_CHANNELS_JSON: str


# ============================================================
# CONFIGURATION
# ============================================================


@dataclass(
    frozen=True,
    slots=True,
)
class HardwareConfiguration:
    """
    Fully validated AquaMind hardware configuration.

    No GPIO resources are opened by this object.
    """

    enabled: bool

    gpio_chip: int | None

    allowed_bcm_pins: frozenset[
        int
    ]

    relay_channels: tuple[
        RelayChannelConfig,
        ...
    ]


# ============================================================
# GPIO CHIP
# ============================================================


def _parse_gpio_chip(
    raw: str,
) -> int | None:
    normalized = raw.strip()

    if not normalized:
        return None

    try:
        chip = int(
            normalized
        )

    except ValueError as exc:
        raise HardwareConfigurationError(
            "HARDWARE_GPIO_CHIP must be "
            "a non-negative integer"
        ) from exc

    if chip < 0:
        raise HardwareConfigurationError(
            "HARDWARE_GPIO_CHIP must be "
            "a non-negative integer"
        )

    return chip


# ============================================================
# BCM PIN ALLOWLIST
# ============================================================


def _parse_allowed_bcm_pins(
    raw: str,
) -> frozenset[int]:
    normalized = raw.strip()

    if not normalized:
        return frozenset()

    parts = [
        part.strip()
        for part in normalized.split(",")
    ]

    if any(
        not part
        for part in parts
    ):
        raise HardwareConfigurationError(
            "HARDWARE_ALLOWED_BCM_PINS "
            "contains an empty pin value"
        )

    pins: list[int] = []

    for part in parts:
        try:
            pin = int(part)

        except ValueError as exc:
            raise HardwareConfigurationError(
                "HARDWARE_ALLOWED_BCM_PINS "
                "must contain only integers"
            ) from exc

        if pin < 0 or pin > 27:
            raise HardwareConfigurationError(
                "Allowed BCM GPIO pins must be "
                "between 0 and 27"
            )

        pins.append(
            pin
        )

    if (
        len(set(pins))
        != len(pins)
    ):
        raise HardwareConfigurationError(
            "HARDWARE_ALLOWED_BCM_PINS "
            "contains duplicate pins"
        )

    return frozenset(
        pins
    )


# ============================================================
# RELAY CHANNELS
# ============================================================


def _parse_relay_channels(
    raw: str,
) -> tuple[
    RelayChannelConfig,
    ...
]:
    try:
        payload = json.loads(
            raw
        )

    except json.JSONDecodeError as exc:
        raise HardwareConfigurationError(
            "HARDWARE_RELAY_CHANNELS_JSON "
            "must contain valid JSON"
        ) from exc

    if not isinstance(
        payload,
        list,
    ):
        raise HardwareConfigurationError(
            "HARDWARE_RELAY_CHANNELS_JSON "
            "must contain a JSON array"
        )

    channels: list[
        RelayChannelConfig
    ] = []

    allowed_fields = {
        "identifier",
        "actuator_type",
        "bcm_pin",
        "active_high",
    }

    required_fields = {
        "identifier",
        "actuator_type",
        "bcm_pin",
    }

    for index, item in enumerate(
        payload
    ):
        if not isinstance(
            item,
            dict,
        ):
            raise HardwareConfigurationError(
                "Relay channel "
                f"{index} must be a JSON object"
            )

        item_fields = set(
            item.keys()
        )

        missing_fields = (
            required_fields
            - item_fields
        )

        if missing_fields:
            raise HardwareConfigurationError(
                "Relay channel "
                f"{index} is missing required fields: "
                + ", ".join(
                    sorted(
                        missing_fields
                    )
                )
            )

        unknown_fields = (
            item_fields
            - allowed_fields
        )

        if unknown_fields:
            raise HardwareConfigurationError(
                "Relay channel "
                f"{index} contains unknown fields: "
                + ", ".join(
                    sorted(
                        unknown_fields
                    )
                )
            )

        identifier = item[
            "identifier"
        ]

        if (
            not isinstance(
                identifier,
                str,
            )
            or not identifier.strip()
        ):
            raise HardwareConfigurationError(
                "Relay channel identifier "
                "must be a non-empty string"
            )

        actuator_type_raw = item[
            "actuator_type"
        ]

        if not isinstance(
            actuator_type_raw,
            str,
        ):
            raise HardwareConfigurationError(
                "Relay channel actuator_type "
                "must be a string"
            )

        try:
            actuator_type = (
                ActuatorType(
                    actuator_type_raw
                )
            )

        except ValueError as exc:
            raise HardwareConfigurationError(
                "Unsupported relay actuator type: "
                f"{actuator_type_raw}"
            ) from exc

        bcm_pin = item[
            "bcm_pin"
        ]

        if (
            not isinstance(
                bcm_pin,
                int,
            )
            or isinstance(
                bcm_pin,
                bool,
            )
        ):
            raise HardwareConfigurationError(
                "Relay channel bcm_pin "
                "must be an integer"
            )

        if (
            bcm_pin < 0
            or bcm_pin > 27
        ):
            raise HardwareConfigurationError(
                "Relay BCM GPIO pin must be "
                "between 0 and 27"
            )

        active_high = item.get(
            "active_high",
            False,
        )

        if not isinstance(
            active_high,
            bool,
        ):
            raise HardwareConfigurationError(
                "Relay channel active_high "
                "must be a boolean"
            )

        channels.append(
            RelayChannelConfig(
                identifier=(
                    identifier.strip()
                ),
                actuator_type=(
                    actuator_type
                ),
                bcm_pin=bcm_pin,
                active_high=(
                    active_high
                ),
            )
        )

    return tuple(
        channels
    )


# ============================================================
# BUILD CONFIGURATION
# ============================================================


def build_hardware_configuration(
    settings: HardwareSettings,
) -> HardwareConfiguration:
    """
    Build and validate AquaMind deployment hardware settings.

    When hardware is disabled, GPIO-specific configuration is
    intentionally ignored. This permits Windows/dev/test
    environments to run without Raspberry Pi configuration.

    When hardware is enabled, configuration is validated
    completely before any GPIO backend is created.
    """

    # --------------------------------------------------------
    # HARDWARE DISABLED
    # --------------------------------------------------------

    if not settings.HARDWARE_ENABLED:
        return HardwareConfiguration(
            enabled=False,
            gpio_chip=None,
            allowed_bcm_pins=(
                frozenset()
            ),
            relay_channels=(),
        )

    # --------------------------------------------------------
    # GPIO CHIP
    # --------------------------------------------------------

    gpio_chip = _parse_gpio_chip(
        settings.HARDWARE_GPIO_CHIP
    )

    # --------------------------------------------------------
    # ALLOWED GPIO PINS
    # --------------------------------------------------------

    allowed_bcm_pins = (
        _parse_allowed_bcm_pins(
            settings.HARDWARE_ALLOWED_BCM_PINS
        )
    )

    if not allowed_bcm_pins:
        raise HardwareConfigurationError(
            "Hardware is enabled but "
            "HARDWARE_ALLOWED_BCM_PINS is empty"
        )

    # --------------------------------------------------------
    # RELAY CHANNELS
    # --------------------------------------------------------

    relay_channels = (
        _parse_relay_channels(
            settings.HARDWARE_RELAY_CHANNELS_JSON
        )
    )

    if not relay_channels:
        raise HardwareConfigurationError(
            "Hardware is enabled but no relay "
            "channels are configured"
        )

    # --------------------------------------------------------
    # ALLOWLIST ENFORCEMENT
    # --------------------------------------------------------

    for channel in relay_channels:
        if (
            channel.bcm_pin
            not in allowed_bcm_pins
        ):
            raise HardwareConfigurationError(
                "Relay channel "
                f"{channel.identifier} uses BCM GPIO "
                f"{channel.bcm_pin}, which is not in "
                "HARDWARE_ALLOWED_BCM_PINS"
            )

    # --------------------------------------------------------
    # REGISTRY VALIDATION
    #
    # Reuse the already-tested hardware registry to validate:
    #
    # - duplicate identifiers;
    # - duplicate GPIO pins;
    # - BCM range.
    # --------------------------------------------------------

    try:
        RelayHardwareRegistry(
            relay_channels
        )

    except ValueError as exc:
        raise HardwareConfigurationError(
            str(exc)
        ) from exc

    return HardwareConfiguration(
        enabled=True,
        gpio_chip=gpio_chip,
        allowed_bcm_pins=(
            allowed_bcm_pins
        ),
        relay_channels=(
            relay_channels
        ),
    )