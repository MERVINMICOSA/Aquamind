from __future__ import annotations

from typing import Protocol


class GPIOBackend(Protocol):
    """
    Low-level Raspberry Pi GPIO abstraction.

    The relay driver depends on this interface instead of
    directly depending on RPi.GPIO/gpiozero.

    Phase 9C will provide the real Raspberry Pi implementation.
    """

    def setup_output(
        self,
        bcm_pin: int,
        *,
        initial_high: bool,
    ) -> None:
        """
        Configure a BCM GPIO pin as an output with an explicit
        initial electrical level.
        """

        ...

    def write(
        self,
        bcm_pin: int,
        *,
        high: bool,
    ) -> None:
        """
        Set the electrical output level.
        """

        ...

    def read(
        self,
        bcm_pin: int,
    ) -> bool:
        """
        Read back the GPIO output level.

        This confirms the GPIO state, not physical water flow,
        motor rotation, or other external equipment behavior.
        """

        ...

    def cleanup(
        self,
    ) -> None:
        """
        Release GPIO resources.
        """

        ...