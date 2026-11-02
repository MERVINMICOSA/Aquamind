from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.hardware.ds18b20_reader import (
    DEFAULT_W1_DEVICES_ROOT,
    DS18B20Reader,
)
from app.hardware.sensor_registry import (
    HardwareSensorReaderRegistry,
    HardwareSensorReaderRoute,
)
from app.services.actuator_executor import (
    ActuatorExecutor,
)
from app.services.hardware_sensor_polling_service import (
    HardwareSensorPollingRuntime,
)
from app.services.hardware_sensor_worker import (
    HardwareSensorWorker,
)


# ============================================================
# RUNTIME COMPONENTS
# ============================================================


@dataclass(
    frozen=True,
    slots=True,
)
class HardwareSensorRuntime:
    """
    Fully composed AquaMind physical-sensor runtime.

    Keeping the concrete components visible makes startup,
    shutdown, testing, diagnostics, and future health checks
    possible without relying on private implementation state.
    """

    ds18b20_reader: DS18B20Reader

    reader_registry: (
        HardwareSensorReaderRegistry
    )

    polling_runtime: (
        HardwareSensorPollingRuntime
    )

    worker: HardwareSensorWorker


# ============================================================
# BUILDER
# ============================================================


def build_hardware_sensor_runtime(
    *,
    session_factory: Callable[
        [],
        AsyncSession,
    ],
    actuator_executor: (
        ActuatorExecutor | None
    ) = None,
    ds18b20_devices_root: (
        str | Path
    ) = DEFAULT_W1_DEVICES_ROOT,
    discovery_interval_seconds: (
        float
    ) = 5.0,
) -> HardwareSensorRuntime:
    """
    Compose the Raspberry Pi physical-sensor runtime.

    Current confirmed hardware adapter:

        DS18B20

    Reader routing is based on the physical hardware
    identifier, not SensorType.

    Therefore a DS18B20 can later represent either:

        WATER_TEMPERATURE
        AIR_TEMPERATURE

    depending on the AquaMind Sensor configuration.

    pH, TDS, and water-level adapters are intentionally not
    registered until their real modules/interfaces are known.
    """

    # ========================================================
    # DS18B20
    # ========================================================

    ds18b20_reader = (
        DS18B20Reader(
            devices_root=(
                ds18b20_devices_root
            )
        )
    )

    # ========================================================
    # HARDWARE READER ROUTING
    # ========================================================

    reader_registry = (
        HardwareSensorReaderRegistry(
            [
                HardwareSensorReaderRoute(
                    name="ds18b20",
                    matches=(
                        DS18B20Reader
                        .supports_identifier
                    ),
                    reader=(
                        ds18b20_reader
                    ),
                ),
            ]
        )
    )

    # ========================================================
    # POLLING RUNTIME
    # ========================================================

    polling_runtime = (
        HardwareSensorPollingRuntime(
            reader_registry=(
                reader_registry
            ),
            actuator_executor=(
                actuator_executor
            ),
        )
    )

    # ========================================================
    # BACKGROUND WORKER
    # ========================================================

    worker = HardwareSensorWorker(
        session_factory=(
            session_factory
        ),
        polling_runtime=(
            polling_runtime
        ),
        discovery_interval_seconds=(
            discovery_interval_seconds
        ),
    )

    # ========================================================
    # COMPOSED RUNTIME
    # ========================================================

    return HardwareSensorRuntime(
        ds18b20_reader=(
            ds18b20_reader
        ),
        reader_registry=(
            reader_registry
        ),
        polling_runtime=(
            polling_runtime
        ),
        worker=worker,
    )