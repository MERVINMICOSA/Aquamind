from __future__ import annotations

from threading import RLock
from typing import Any

from app.hardware.driver import (
    HardwareActuatorDriverError,
)


# ============================================================
# OPTIONAL RASPBERRY PI IMPORT
# ============================================================


def _load_gpiozero_components():
    """
    Load Raspberry Pi GPIO dependencies only when actual
    hardware initialization is attempted.

    This deliberately avoids importing gpiozero/lgpio at module
    import time so the AquaMind backend and automated tests can
    continue running on Windows development machines.
    """

    try:
        from gpiozero import OutputDevice
        from gpiozero.pins.lgpio import LGPIOFactory

    except ImportError as exc:
        raise HardwareActuatorDriverError(
            "Raspberry Pi GPIO backend is unavailable",
            fault_code="gpio_backend_unavailable",
        ) from exc

    return OutputDevice, LGPIOFactory


# ============================================================
# GPIO ZERO BACKEND
# ============================================================


class GPIOZeroBackend:
    """
    Concrete GPIOBackend implemented with GPIO Zero + LGPIO.

    Safety properties:

    - GPIO libraries are loaded lazily;
    - only explicitly allowed BCM pins may be used;
    - GPIO chip selection is configurable;
    - duplicate output initialization is rejected;
    - unconfigured GPIO access is rejected;
    - GPIO/device resources are released on cleanup;
    - backend failures are converted into expected hardware
      errors understood by RaspberryPiActuatorExecutor.

    GPIO numbering is BCM numbering, not physical header
    numbering.
    """

    def __init__(
        self,
        *,
        allowed_bcm_pins: set[int]
        | frozenset[int],
        chip: int | None = None,
    ) -> None:
        normalized_pins = frozenset(
            allowed_bcm_pins
        )

        if not normalized_pins:
            raise ValueError(
                "allowed_bcm_pins cannot be empty"
            )

        for pin in normalized_pins:
            if (
                not isinstance(pin, int)
                or isinstance(pin, bool)
            ):
                raise ValueError(
                    "Allowed BCM GPIO pins must be integers"
                )

            if pin < 0 or pin > 27:
                raise ValueError(
                    "Allowed BCM GPIO pins must be "
                    "between 0 and 27"
                )

        if (
            chip is not None
            and (
                not isinstance(chip, int)
                or isinstance(chip, bool)
                or chip < 0
            )
        ):
            raise ValueError(
                "GPIO chip must be a non-negative integer"
            )

        self._allowed_bcm_pins = (
            normalized_pins
        )

        self._chip = chip

        self._factory: Any | None = None
        self._output_device_class: Any | None = None

        self._devices: dict[
            int,
            Any,
        ] = {}

        self._lock = RLock()

    # ========================================================
    # CONFIGURATION
    # ========================================================

    @property
    def allowed_bcm_pins(
        self,
    ) -> frozenset[int]:
        return self._allowed_bcm_pins

    @property
    def chip(
        self,
    ) -> int | None:
        return self._chip

    # ========================================================
    # INTERNAL HELPERS
    # ========================================================

    def _require_allowed_pin(
        self,
        bcm_pin: int,
    ) -> None:
        if (
            bcm_pin
            not in self._allowed_bcm_pins
        ):
            raise HardwareActuatorDriverError(
                f"BCM GPIO pin {bcm_pin} is not "
                "allowed by hardware configuration",
                fault_code="gpio_pin_not_allowed",
            )

    def _ensure_factory(
        self,
    ) -> None:
        if self._factory is not None:
            return

        (
            output_device_class,
            factory_class,
        ) = _load_gpiozero_components()

        try:
            if self._chip is None:
                factory = factory_class()
            else:
                factory = factory_class(
                    chip=self._chip
                )

        except Exception as exc:
            raise HardwareActuatorDriverError(
                "Failed to initialize Raspberry Pi "
                "GPIO pin factory",
                fault_code=(
                    "gpio_factory_initialization_failed"
                ),
            ) from exc

        self._output_device_class = (
            output_device_class
        )

        self._factory = factory

    def _require_device(
        self,
        bcm_pin: int,
    ):
        self._require_allowed_pin(
            bcm_pin
        )

        device = self._devices.get(
            bcm_pin
        )

        if device is None:
            raise HardwareActuatorDriverError(
                f"BCM GPIO pin {bcm_pin} is not configured",
                fault_code="gpio_pin_not_configured",
            )

        return device

    # ========================================================
    # GPIO BACKEND CONTRACT
    # ========================================================

    def setup_output(
        self,
        bcm_pin: int,
        *,
        initial_high: bool,
    ) -> None:
        """
        Configure one explicitly allowed BCM GPIO as output.

        OutputDevice is configured active_high=True so its
        logical on/off operations correspond directly to raw
        electrical HIGH/LOW.

        Relay active-low/active-high behavior remains owned by
        RelayActuatorDriver rather than this backend.
        """

        with self._lock:
            self._require_allowed_pin(
                bcm_pin
            )

            if bcm_pin in self._devices:
                raise HardwareActuatorDriverError(
                    f"BCM GPIO pin {bcm_pin} is "
                    "already configured",
                    fault_code=(
                        "gpio_pin_already_configured"
                    ),
                )

            self._ensure_factory()

            try:
                device = (
                    self._output_device_class(
                        bcm_pin,
                        active_high=True,
                        initial_value=bool(
                            initial_high
                        ),
                        pin_factory=(
                            self._factory
                        ),
                    )
                )

            except Exception as exc:
                raise HardwareActuatorDriverError(
                    f"Failed to configure BCM GPIO "
                    f"pin {bcm_pin}",
                    fault_code="gpio_setup_failed",
                ) from exc

            self._devices[
                bcm_pin
            ] = device

    def write(
        self,
        bcm_pin: int,
        *,
        high: bool,
    ) -> None:
        """
        Write raw electrical HIGH/LOW to a configured pin.
        """

        with self._lock:
            device = self._require_device(
                bcm_pin
            )

            try:
                if high:
                    device.on()
                else:
                    device.off()

            except Exception as exc:
                raise HardwareActuatorDriverError(
                    f"Failed to write BCM GPIO "
                    f"pin {bcm_pin}",
                    fault_code="gpio_write_failed",
                ) from exc

    def read(
        self,
        bcm_pin: int,
    ) -> bool:
        """
        Read the GPIO Zero output state.

        This verifies the software-visible GPIO output state
        only. It does not prove that a pump, fan, feeder, or
        other external device physically operated.
        """

        with self._lock:
            device = self._require_device(
                bcm_pin
            )

            try:
                return bool(
                    device.value
                )

            except Exception as exc:
                raise HardwareActuatorDriverError(
                    f"Failed to read BCM GPIO "
                    f"pin {bcm_pin}",
                    fault_code="gpio_read_failed",
                ) from exc

    def cleanup(
        self,
    ) -> None:
        """
        Release all GPIO Zero devices and the LGPIO factory.

        Cleanup is best-effort: every resource is attempted
        even if one close operation fails.
        """

        with self._lock:
            first_error: (
                Exception | None
            ) = None

            devices = list(
                self._devices.values()
            )

            self._devices.clear()

            for device in devices:
                try:
                    device.close()

                except Exception as exc:
                    if first_error is None:
                        first_error = exc

            factory = self._factory

            self._factory = None
            self._output_device_class = (
                None
            )

            if factory is not None:
                try:
                    factory.close()

                except Exception as exc:
                    if first_error is None:
                        first_error = exc

            if first_error is not None:
                raise HardwareActuatorDriverError(
                    "Raspberry Pi GPIO cleanup "
                    "did not complete cleanly",
                    fault_code="gpio_cleanup_failed",
                ) from first_error