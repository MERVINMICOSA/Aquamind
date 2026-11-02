from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from app.db.enums import (
    ActuatorCommandType,
    ActuatorType,
)
from app.hardware.driver import (
    HardwareActuatorDriverError,
    HardwareDriverResult,
)
from app.hardware.gpio_backend import (
    GPIOBackend,
)
from app.services.actuator_executor import (
    ActuatorExecutionCommand,
)


# ============================================================
# RELAY CONFIGURATION
# ============================================================


@dataclass(
    frozen=True,
    slots=True,
)
class RelayChannelConfig:
    """
    Physical relay-channel configuration.

    identifier
        Stable logical identifier stored in
        Actuator.hardware_identifier.

    actuator_type
        Protects against accidentally routing the wrong
        actuator type to a physical relay channel.

    bcm_pin
        Raspberry Pi Broadcom GPIO number.

    active_high
        True:
            electrical HIGH = relay ON

        False:
            electrical LOW = relay ON

        Many relay boards are active-low, so False is the
        safer explicit default.
    """

    identifier: str
    actuator_type: ActuatorType
    bcm_pin: int
    active_high: bool = False


# ============================================================
# HARDWARE REGISTRY
# ============================================================


class RelayHardwareRegistry:
    """
    Immutable mapping between logical AquaMind hardware
    identifiers and Raspberry Pi relay channels.
    """

    def __init__(
        self,
        channels: list[RelayChannelConfig]
        | tuple[RelayChannelConfig, ...],
    ) -> None:
        by_identifier: dict[
            str,
            RelayChannelConfig,
        ] = {}

        used_pins: dict[
            int,
            str,
        ] = {}

        for channel in channels:
            identifier = (
                channel.identifier.strip()
            )

            if not identifier:
                raise ValueError(
                    "Relay hardware identifier "
                    "cannot be empty"
                )

            if identifier in by_identifier:
                raise ValueError(
                    "Duplicate relay hardware identifier: "
                    f"{identifier}"
                )

            # BCM GPIO numbers exposed by standard Raspberry Pi
            # GPIO headers are within this range.
            #
            # Phase 9C deployment configuration will further
            # restrict which GPIOs AquaMind actually permits.
            if (
                channel.bcm_pin < 0
                or channel.bcm_pin > 27
            ):
                raise ValueError(
                    "Relay BCM GPIO pin must be "
                    "between 0 and 27"
                )

            existing_identifier = (
                used_pins.get(
                    channel.bcm_pin
                )
            )

            if existing_identifier is not None:
                raise ValueError(
                    "BCM GPIO pin "
                    f"{channel.bcm_pin} is already assigned "
                    f"to {existing_identifier}"
                )

            normalized = RelayChannelConfig(
                identifier=identifier,
                actuator_type=(
                    channel.actuator_type
                ),
                bcm_pin=channel.bcm_pin,
                active_high=(
                    channel.active_high
                ),
            )

            by_identifier[
                identifier
            ] = normalized

            used_pins[
                channel.bcm_pin
            ] = identifier

        self._channels = (
            by_identifier
        )

    def resolve(
        self,
        identifier: str,
    ) -> RelayChannelConfig:
        normalized = (
            identifier.strip()
        )

        channel = self._channels.get(
            normalized
        )

        if channel is None:
            raise HardwareActuatorDriverError(
                "Unknown actuator hardware identifier",
                fault_code=(
                    "unknown_hardware_identifier"
                ),
            )

        return channel

    @property
    def channels(
        self,
    ) -> tuple[
        RelayChannelConfig,
        ...
    ]:
        return tuple(
            self._channels.values()
        )


# ============================================================
# SAFE RELAY DRIVER
# ============================================================


class RelayActuatorDriver:
    """
    HardwareActuatorDriver implementation for binary relay
    outputs.

    Safety properties:

    - every configured relay is initialized OFF;
    - duplicate GPIO assignments are rejected;
    - actuator type must match the configured channel;
    - electrical state is read back after writes;
    - unsupported variable-value commands are rejected;
    - EMERGENCY_STOP always maps to OFF;
    - close() attempts to return every relay to OFF;
    - GPIO operations are serialized because many GPIO
      libraries are not thread-safe.
    """

    def __init__(
        self,
        *,
        backend: GPIOBackend,
        registry: RelayHardwareRegistry,
    ) -> None:
        self._backend = backend
        self._registry = registry

        self._initialized = False
        self._lock = RLock()

    # ========================================================
    # ELECTRICAL STATE MAPPING
    # ========================================================

    @staticmethod
    def _electrical_level(
        channel: RelayChannelConfig,
        *,
        logical_on: bool,
    ) -> bool:
        """
        Convert logical actuator state into GPIO HIGH/LOW.
        """

        if logical_on:
            return channel.active_high

        return not channel.active_high

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def initialize(
        self,
    ) -> None:
        """
        Configure every relay output into its safe OFF state.

        Initialization never intentionally energizes an
        actuator.
        """

        with self._lock:
            if self._initialized:
                return

            configured: list[
                RelayChannelConfig
            ] = []

            try:
                for channel in (
                    self._registry.channels
                ):
                    off_high = (
                        self._electrical_level(
                            channel,
                            logical_on=False,
                        )
                    )

                    self._backend.setup_output(
                        channel.bcm_pin,
                        initial_high=off_high,
                    )

                    configured.append(
                        channel
                    )

                    observed_high = (
                        self._backend.read(
                            channel.bcm_pin
                        )
                    )

                    if (
                        observed_high
                        != off_high
                    ):
                        raise HardwareActuatorDriverError(
                            "GPIO output did not enter "
                            "safe OFF state",
                            fault_code=(
                                "gpio_initialization_mismatch"
                            ),
                        )

            except Exception:
                # Best-effort safety shutdown for anything
                # successfully configured before failure.
                for channel in configured:
                    try:
                        self._backend.write(
                            channel.bcm_pin,
                            high=(
                                self._electrical_level(
                                    channel,
                                    logical_on=False,
                                )
                            ),
                        )
                    except Exception:
                        pass

                try:
                    self._backend.cleanup()
                except Exception:
                    pass

                raise

            self._initialized = True

    # ========================================================
    # COMMAND RESOLUTION
    # ========================================================

    @staticmethod
    def _resolve_logical_state(
        command: ActuatorExecutionCommand,
    ) -> bool:
        if (
            command.command_type
            == ActuatorCommandType.ACTIVATE
        ):
            return True

        if command.command_type in (
            ActuatorCommandType.DEACTIVATE,
            ActuatorCommandType.EMERGENCY_STOP,
        ):
            return False

        raise HardwareActuatorDriverError(
            "Relay driver does not support "
            "this actuator command",
            fault_code=(
                "unsupported_relay_command"
            ),
        )

    # ========================================================
    # EXECUTION
    # ========================================================

    def execute(
        self,
        command: ActuatorExecutionCommand,
    ) -> HardwareDriverResult:
        with self._lock:
            if not self._initialized:
                raise HardwareActuatorDriverError(
                    "Relay hardware driver "
                    "is not initialized",
                    fault_code=(
                        "hardware_not_initialized"
                    ),
                )

            identifier = (
                command.hardware_identifier
            )

            if (
                identifier is None
                or not identifier.strip()
            ):
                raise HardwareActuatorDriverError(
                    "Actuator has no hardware identifier",
                    fault_code=(
                        "missing_hardware_identifier"
                    ),
                )

            channel = (
                self._registry.resolve(
                    identifier
                )
            )

            # ------------------------------------------------
            # TYPE SAFETY
            # ------------------------------------------------

            if (
                channel.actuator_type
                != command.actuator_type
            ):
                raise HardwareActuatorDriverError(
                    "Actuator type does not match "
                    "configured relay channel",
                    fault_code=(
                        "hardware_type_mismatch"
                    ),
                )

            logical_on = (
                self._resolve_logical_state(
                    command
                )
            )

            expected_high = (
                self._electrical_level(
                    channel,
                    logical_on=logical_on,
                )
            )

            # ------------------------------------------------
            # WRITE GPIO
            # ------------------------------------------------

            self._backend.write(
                channel.bcm_pin,
                high=expected_high,
            )

            # ------------------------------------------------
            # READBACK
            #
            # This confirms the GPIO output level only.
            # It must not be interpreted as confirmation of
            # pump flow, fan rotation, feeding, etc.
            # ------------------------------------------------

            observed_high = (
                self._backend.read(
                    channel.bcm_pin
                )
            )

            if (
                observed_high
                != expected_high
            ):
                raise HardwareActuatorDriverError(
                    "GPIO output state did not match "
                    "requested relay state",
                    fault_code=(
                        "gpio_state_mismatch"
                    ),
                )

            actual_value = (
                1.0
                if logical_on
                else 0.0
            )

            state_name = (
                "activated"
                if logical_on
                else "deactivated"
            )

            return HardwareDriverResult(
                actual_value=actual_value,
                result_summary=(
                    f"Relay output {state_name}"
                ),
            )

    # ========================================================
    # SHUTDOWN
    # ========================================================

    def close(
        self,
    ) -> None:
        """
        Best-effort fail-safe shutdown.

        All known relay channels are commanded OFF before GPIO
        resources are released.
        """

        with self._lock:
            first_error: Exception | None = None

            if self._initialized:
                for channel in (
                    self._registry.channels
                ):
                    try:
                        self._backend.write(
                            channel.bcm_pin,
                            high=(
                                self._electrical_level(
                                    channel,
                                    logical_on=False,
                                )
                            ),
                        )

                    except Exception as exc:
                        if first_error is None:
                            first_error = exc

            try:
                self._backend.cleanup()

            except Exception as exc:
                if first_error is None:
                    first_error = exc

            finally:
                self._initialized = False

            if first_error is not None:
                raise HardwareActuatorDriverError(
                    "Relay hardware shutdown "
                    "did not complete cleanly",
                    fault_code=(
                        "hardware_shutdown_failed"
                    ),
                ) from first_error