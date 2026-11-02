from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from enum import Enum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    SensorType,
)
from app.hardware.sensor_reader import (
    HardwareSensorReader,
    HardwareSensorReadError,
)
from app.models.sensors import (
    Sensor,
)
from app.services.actuator_executor import (
    ActuatorExecutor,
)
from app.services.hardware_sensor_acquisition_service import (
    HardwareSensorAcquisitionError,
    acquire_hardware_sensor_reading,
)


# ============================================================
# EXCEPTIONS
# ============================================================


class HardwareSensorPollingError(
    ValueError
):
    """Raised when the polling runtime itself is invalid."""


# ============================================================
# POLLING OUTCOMES
# ============================================================


class HardwareSensorPollingOutcome(
    str,
    Enum,
):
    ACQUIRED = "acquired"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


# ============================================================
# POLLING RESULT
# ============================================================


@dataclass(
    frozen=True,
    slots=True,
)
class HardwareSensorPollingResult:
    sensor_id: UUID
    sensor_type: SensorType

    outcome: (
        HardwareSensorPollingOutcome
    )

    reading_id: UUID | None = None

    fault_code: str | None = None
    error_message: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class HardwareSensorPollingCycleResult:
    started_at: datetime

    sensor_results: tuple[
        HardwareSensorPollingResult,
        ...
    ]

    @property
    def attempted_count(
        self,
    ) -> int:
        return len(
            self.sensor_results
        )

    @property
    def acquired_count(
        self,
    ) -> int:
        return sum(
            result.outcome
            == HardwareSensorPollingOutcome.ACQUIRED
            for result in self.sensor_results
        )

    @property
    def failed_count(
        self,
    ) -> int:
        return sum(
            result.outcome
            == HardwareSensorPollingOutcome.FAILED
            for result in self.sensor_results
        )

    @property
    def unsupported_count(
        self,
    ) -> int:
        return sum(
            result.outcome
            == HardwareSensorPollingOutcome.UNSUPPORTED
            for result in self.sensor_results
        )


# ============================================================
# READER REGISTRY
# ============================================================


from app.hardware.sensor_registry import (
    HardwareSensorReaderRegistry,
    HardwareSensorRoutingError,
)

# ============================================================
# CLOCK
# ============================================================


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def _require_aware_datetime(
    value: datetime,
) -> datetime:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise HardwareSensorPollingError(
            "Sensor polling time must be "
            "timezone-aware"
        )

    return value


# ============================================================
# POLLING RUNTIME
# ============================================================


class HardwareSensorPollingRuntime:
    """
    Schedule physical sensor acquisitions according to each
    Sensor.sampling_interval_seconds value.

    Important properties:

    - only enabled, non-deleted, non-simulated sensors are
      considered;
    - the database-defined sampling interval is respected;
    - a sensor is due immediately on first discovery;
    - one expected hardware failure does not prevent another
      sensor from being acquired;
    - unsupported sensor types are isolated rather than
      crashing the polling runtime;
    - acquisition is sequential on the supplied AsyncSession;
      the same SQLAlchemy session is never used concurrently;
    - the next poll is scheduled from the attempt time even
      when hardware acquisition fails, preventing a failing
      sensor from being hammered continuously.
    """

    def __init__(
        self,
        *,
        reader_registry: (
            HardwareSensorReaderRegistry
        ),
        actuator_executor: (
            ActuatorExecutor | None
        ) = None,
    ) -> None:
        self._reader_registry = (
            reader_registry
        )

        self._actuator_executor = (
            actuator_executor
        )

        self._next_due_at: dict[
            UUID,
            datetime,
        ] = {}

    # ========================================================
    # NEXT-DUE INSPECTION
    # ========================================================

    def next_due_at(
        self,
        sensor_id: UUID,
    ) -> datetime | None:
        return self._next_due_at.get(
            sensor_id
        )
    

    def next_scheduled_at(
        self,
    ) -> datetime | None:
        """
        Return the earliest scheduled hardware sensor acquisition.

        Used by the background worker to avoid unnecessarily
        querying the database in a tight fixed-frequency loop.
        """

        if not self._next_due_at:
            return None

        return min(
            self._next_due_at.values()
        )

    # ========================================================
    # RUN ONE POLLING CYCLE
    # ========================================================

    async def run_cycle(
        self,
        session: AsyncSession,
        *,
        current_time: (
            datetime | None
        ) = None,
    ) -> HardwareSensorPollingCycleResult:
        polling_time = (
            _require_aware_datetime(
                current_time
                or _utc_now()
            )
        )

        # ----------------------------------------------------
        # PHYSICAL SENSOR INVENTORY
        #
        # Missing hardware identifiers are deliberately not
        # filtered here.
        #
        # A supported physical sensor with no identifier is a
        # configuration error and should be surfaced by the
        # acquisition service rather than silently disappearing.
        # ----------------------------------------------------

        sensor_result = await session.execute(
            select(Sensor)
            .where(
                Sensor.deleted_at.is_(None),
                Sensor.is_enabled.is_(True),
                Sensor.is_simulated.is_(False),
            )
            .order_by(
                Sensor.id.asc()
            )
        )

        sensors = list(
            sensor_result
            .scalars()
            .all()
        )

        # ----------------------------------------------------
        # REMOVE STALE SCHEDULE ENTRIES
        #
        # Sensors disabled/deleted/changed to simulation mode
        # stop participating in the runtime.
        # ----------------------------------------------------

        active_sensor_ids = {
            sensor.id
            for sensor in sensors
        }

        stale_sensor_ids = (
            set(
                self._next_due_at
            )
            - active_sensor_ids
        )

        for sensor_id in (
            stale_sensor_ids
        ):
            self._next_due_at.pop(
                sensor_id,
                None,
            )

        results: list[
            HardwareSensorPollingResult
        ] = []

        # ----------------------------------------------------
        # PROCESS DUE SENSORS
        #
        # Sequential by design:
        #
        # AsyncSession must not be used concurrently.
        # ----------------------------------------------------

        for sensor in sensors:
            next_due = (
                self._next_due_at.get(
                    sensor.id
                )
            )

            if (
                next_due is not None
                and polling_time < next_due
            ):
                continue

            sampling_interval = (
                sensor.sampling_interval_seconds
            )

            if sampling_interval <= 0:
                results.append(
                    HardwareSensorPollingResult(
                        sensor_id=sensor.id,
                        sensor_type=(
                            sensor.sensor_type
                        ),
                        outcome=(
                            HardwareSensorPollingOutcome.FAILED
                        ),
                        fault_code=(
                            "invalid_sampling_interval"
                        ),
                        error_message=(
                            "Sensor sampling interval "
                            "must be greater than zero"
                        ),
                    )
                )

                # Do not create an invalid timedelta and do not
                # pretend acquisition occurred.
                continue

            # ------------------------------------------------
            # SCHEDULE NEXT ATTEMPT FIRST
            #
            # Hardware failure must not cause an immediate
            # tight retry loop against the device.
            # ------------------------------------------------

            self._next_due_at[
                sensor.id
            ] = (
                polling_time
                + timedelta(
                    seconds=(
                        sampling_interval
                    )
                )
            )

            # ------------------------------------------------
            # RESOLVE PHYSICAL HARDWARE ADAPTER
            #
            # Routing is based on hardware_identifier, not
            # SensorType.
            #
            # SensorType describes what the sensor represents.
            # The identifier determines how its physical device
            # is read.
            # ------------------------------------------------

            try:
                reader = (
                    self._reader_registry.resolve(
                        sensor.hardware_identifier
                    )
                )

            except HardwareSensorRoutingError as exc:
                results.append(
                    HardwareSensorPollingResult(
                        sensor_id=sensor.id,
                        sensor_type=(
                            sensor.sensor_type
                        ),
                        outcome=(
                            HardwareSensorPollingOutcome.FAILED
                        ),
                        fault_code=(
                            "sensor_reader_routing_failed"
                        ),
                        error_message=(
                            str(exc).strip()
                            or "Hardware sensor reader "
                            "routing failed"
                        ),
                    )
                )

                continue

            if reader is None:
                results.append(
                    HardwareSensorPollingResult(
                        sensor_id=sensor.id,
                        sensor_type=(
                            sensor.sensor_type
                        ),
                        outcome=(
                            HardwareSensorPollingOutcome.UNSUPPORTED
                        ),
                        fault_code=(
                            "unsupported_sensor_reader"
                        ),
                        error_message=(
                            "No hardware reader is "
                            "registered for this "
                            "hardware identifier"
                        ),
                    )
                )

                continue
            # ------------------------------------------------
            # ACQUIRE
            # ------------------------------------------------

            try:
                reading = (
                    await acquire_hardware_sensor_reading(
                        session,
                        sensor_id=sensor.id,
                        reader=reader,
                        actuator_executor=(
                            self._actuator_executor
                        ),
                    )
                )

            except HardwareSensorReadError as exc:
                results.append(
                    HardwareSensorPollingResult(
                        sensor_id=sensor.id,
                        sensor_type=(
                            sensor.sensor_type
                        ),
                        outcome=(
                            HardwareSensorPollingOutcome.FAILED
                        ),
                        fault_code=(
                            exc.fault_code
                        ),
                        error_message=(
                            str(exc).strip()
                            or "Hardware sensor read failed"
                        ),
                    )
                )

                continue

            except HardwareSensorAcquisitionError as exc:
                results.append(
                    HardwareSensorPollingResult(
                        sensor_id=sensor.id,
                        sensor_type=(
                            sensor.sensor_type
                        ),
                        outcome=(
                            HardwareSensorPollingOutcome.FAILED
                        ),
                        fault_code=(
                            "sensor_acquisition_failed"
                        ),
                        error_message=(
                            str(exc).strip()
                            or "Hardware sensor "
                            "acquisition failed"
                        ),
                    )
                )

                continue

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            results.append(
                HardwareSensorPollingResult(
                    sensor_id=sensor.id,
                    sensor_type=(
                        sensor.sensor_type
                    ),
                    outcome=(
                        HardwareSensorPollingOutcome.ACQUIRED
                    ),
                    reading_id=(
                        reading.id
                    ),
                )
            )

        return (
            HardwareSensorPollingCycleResult(
                started_at=polling_time,
                sensor_results=tuple(
                    results
                ),
            )
        )