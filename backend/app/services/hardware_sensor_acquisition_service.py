from __future__ import annotations

import asyncio
import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    ReadingQuality,
    ReadingSource,
)
from app.models.sensors import (
    Sensor,
    SensorReading,
)
from app.hardware.sensor_reader import (
    HardwareSensorReader,
    HardwareSensorReading,
)
from app.services.actuator_executor import (
    ActuatorExecutor,
)
from app.services.alert_service import (
    process_sensor_reading,
)
from app.services.sensor_automation_service import (
    process_sensor_reading_automation,
)


# ============================================================
# EXCEPTIONS
# ============================================================


class HardwareSensorAcquisitionError(
    ValueError
):
    """
    Raised when AquaMind cannot safely convert a hardware
    sensor result into persisted telemetry.

    HardwareSensorReadError raised by a concrete reader is
    intentionally allowed to propagate unchanged so its
    hardware fault_code is preserved.
    """


# ============================================================
# RESULT VALIDATION
# ============================================================


def _validate_hardware_result(
    *,
    configured_identifier: str,
    result: HardwareSensorReading,
) -> tuple[
    float,
    str,
]:
    """
    Validate the hardware-neutral reader result before it is
    allowed into AquaMind telemetry.
    """

    if not isinstance(
        result,
        HardwareSensorReading,
    ):
        raise HardwareSensorAcquisitionError(
            "Hardware sensor reader returned "
            "an invalid result"
        )

    result_identifier = (
        result.hardware_identifier
        .strip()
    )

    if not result_identifier:
        raise HardwareSensorAcquisitionError(
            "Hardware sensor reader returned "
            "an empty hardware identifier"
        )

    # Hardware identifiers are treated case-insensitively for
    # comparison. This supports identifiers such as DS18B20
    # ROM IDs while still preserving the reader's normalized
    # identifier.
    if (
        result_identifier.lower()
        != configured_identifier.lower()
    ):
        raise HardwareSensorAcquisitionError(
            "Hardware sensor reading does not match "
            "the configured sensor"
        )

    try:
        value_numeric = float(
            result.value_numeric
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise HardwareSensorAcquisitionError(
            "Hardware sensor returned "
            "a non-numeric value"
        ) from exc

    if not math.isfinite(
        value_numeric
    ):
        raise HardwareSensorAcquisitionError(
            "Hardware sensor returned "
            "a non-finite value"
        )

    recorded_at = (
        result.recorded_at
    )

    if (
        recorded_at.tzinfo is None
        or recorded_at.utcoffset()
        is None
    ):
        raise HardwareSensorAcquisitionError(
            "Hardware sensor reading requires "
            "a timezone-aware timestamp"
        )

    return (
        value_numeric,
        result_identifier,
    )


# ============================================================
# ACQUISITION
# ============================================================


async def acquire_hardware_sensor_reading(
    session: AsyncSession,
    *,
    sensor_id: UUID,
    reader: HardwareSensorReader,
    actuator_executor: (
        ActuatorExecutor | None
    ) = None,
) -> SensorReading:
    """
    Acquire and persist one physical sensor reading.

    Runtime order:

    1. Validate the configured AquaMind Sensor.
    2. Read physical hardware outside the async event loop.
    3. Validate the returned hardware result.
    4. Persist a GOOD/HARDWARE SensorReading.
    5. Commit telemetry.
    6. Process alerts.
    7. Process automation only when an actuator executor is
       configured.

    Telemetry is durable before downstream alert or actuator
    processing starts.
    """

    # ========================================================
    # SENSOR CONFIGURATION
    # ========================================================

    sensor = await session.get(
        Sensor,
        sensor_id,
    )

    if (
        sensor is None
        or sensor.deleted_at is not None
    ):
        raise HardwareSensorAcquisitionError(
            "Hardware sensor not found"
        )

    if not sensor.is_enabled:
        raise HardwareSensorAcquisitionError(
            "Hardware sensor is disabled"
        )

    # The hardware acquisition path must never accidentally
    # operate a sensor explicitly configured as simulated.
    if sensor.is_simulated:
        raise HardwareSensorAcquisitionError(
            "Simulated sensor cannot use "
            "hardware acquisition"
        )

    hardware_identifier = (
        sensor.hardware_identifier
    )

    if hardware_identifier is None:
        raise HardwareSensorAcquisitionError(
            "Hardware sensor has no "
            "hardware identifier"
        )

    hardware_identifier = (
        hardware_identifier.strip()
    )

    if not hardware_identifier:
        raise HardwareSensorAcquisitionError(
            "Hardware sensor has no "
            "hardware identifier"
        )

    # ========================================================
    # PHYSICAL READ
    #
    # Hardware readers are synchronous because most Pi sensor
    # drivers/filesystem interfaces are synchronous.
    #
    # Keep them off FastAPI's event loop.
    # ========================================================

    result = await asyncio.to_thread(
        reader.read,
        hardware_identifier,
    )

    # ========================================================
    # RESULT VALIDATION
    # ========================================================

    (
        value_numeric,
        _,
    ) = _validate_hardware_result(
        configured_identifier=(
            hardware_identifier
        ),
        result=result,
    )

    # ========================================================
    # CREATE TELEMETRY
    #
    # A successful physical read becomes GOOD/HARDWARE.
    #
    # Failed hardware reads never reach this point and
    # therefore cannot create fake GOOD telemetry.
    # ========================================================

    reading = SensorReading(
        sensor_id=sensor.id,
        recorded_at=(
            result.recorded_at
        ),
        value_numeric=(
            value_numeric
        ),
        unit=sensor.unit,
        quality_status=(
            ReadingQuality.GOOD
        ),
        source=(
            ReadingSource.HARDWARE
        ),
        sequence_number=None,
    )

    session.add(
        reading
    )

    # ========================================================
    # TELEMETRY COMMIT BOUNDARY
    #
    # Physical telemetry becomes durable before downstream
    # alert/automation processing.
    # ========================================================

    await session.commit()

    await session.refresh(
        reading
    )

    # ========================================================
    # ALERT PROCESSING
    # ========================================================

    await process_sensor_reading(
        session,
        reading,
    )

    # ========================================================
    # AUTOMATION PROCESSING
    #
    # Preserve Phase 8 behavior:
    #
    # no executor
    #     → telemetry remains valid
    #     → alerts still run
    #     → no fake hardware execution
    #
    # configured executor
    #     → existing automation pipeline handles execution.
    # ========================================================

    if actuator_executor is not None:
        await process_sensor_reading_automation(
            session,
            reading=reading,
            executor=actuator_executor,
        )

    return reading