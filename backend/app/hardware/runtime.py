from __future__ import annotations

import asyncio

from app.hardware.configuration import (
    HardwareSettings,
    build_hardware_configuration,
)
from app.hardware.gpiozero_backend import (
    GPIOZeroBackend,
)
from app.hardware.relay_driver import (
    RelayActuatorDriver,
    RelayHardwareRegistry,
)
from app.hardware.raspberry_pi_executor import (
    RaspberryPiActuatorExecutor,
)


# ============================================================
# HARDWARE RUNTIME CONSTRUCTION
# ============================================================


async def build_hardware_actuator_executor(
    settings: HardwareSettings,
) -> RaspberryPiActuatorExecutor | None:
    """
    Build AquaMind's physical actuator execution stack.

    Hardware disabled:
        Return None without opening any GPIO resources.

    Hardware enabled:
        Validate configuration, construct the GPIO/relay stack,
        initialize every configured relay into its safe OFF
        state, and return the actuator executor.

    Any enabled-hardware configuration or initialization failure
    intentionally propagates so application startup fails.
    """

    configuration = (
        build_hardware_configuration(
            settings
        )
    )

    # --------------------------------------------------------
    # HARDWARE DISABLED
    # --------------------------------------------------------

    if not configuration.enabled:
        return None

    # --------------------------------------------------------
    # HARDWARE REGISTRY
    # --------------------------------------------------------

    registry = RelayHardwareRegistry(
        configuration.relay_channels
    )

    # --------------------------------------------------------
    # GPIO BACKEND
    # --------------------------------------------------------

    backend = GPIOZeroBackend(
        allowed_bcm_pins=(
            configuration.allowed_bcm_pins
        ),
        chip=configuration.gpio_chip,
    )

    # --------------------------------------------------------
    # RELAY DRIVER
    # --------------------------------------------------------

    driver = RelayActuatorDriver(
        backend=backend,
        registry=registry,
    )

    # --------------------------------------------------------
    # SAFE INITIALIZATION
    #
    # GPIO libraries are synchronous, so keep initialization
    # off FastAPI's event loop.
    #
    # RelayActuatorDriver.initialize() itself performs
    # best-effort cleanup if initialization fails part-way.
    # --------------------------------------------------------

    await asyncio.to_thread(
        driver.initialize
    )

    # --------------------------------------------------------
    # EXECUTOR
    # --------------------------------------------------------

    try:
        return RaspberryPiActuatorExecutor(
            driver=driver
        )

    except Exception:
        # Defensive cleanup if future executor construction ever
        # performs work that can fail after GPIO initialized.
        try:
            await asyncio.to_thread(
                driver.close
            )
        finally:
            raise


# ============================================================
# HARDWARE RUNTIME SHUTDOWN
# ============================================================


async def shutdown_hardware_actuator_executor(
    executor: RaspberryPiActuatorExecutor | None,
) -> None:
    """
    Shut down AquaMind's hardware execution stack.

    RaspberryPiActuatorExecutor.close() delegates to the relay
    driver, which commands every known relay OFF before GPIO
    cleanup.
    """

    if executor is None:
        return

    await executor.close()