from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import (
    datetime,
    timezone,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.services.hardware_sensor_polling_service import (
    HardwareSensorPollingCycleResult,
    HardwareSensorPollingRuntime,
)


logger = logging.getLogger(
    __name__
)


# ============================================================
# EXCEPTIONS
# ============================================================


class HardwareSensorWorkerError(
    ValueError
):
    """Raised for invalid sensor-worker configuration."""


# ============================================================
# CLOCK
# ============================================================


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


# ============================================================
# BACKGROUND SENSOR WORKER
# ============================================================


class HardwareSensorWorker:
    """
    Long-running Raspberry Pi physical-sensor polling worker.

    Responsibilities:

    - create a fresh AsyncSession for every polling cycle;
    - preserve HardwareSensorPollingRuntime scheduling state;
    - never share one SQLAlchemy AsyncSession across cycles;
    - recover from unexpected/transient cycle failures;
    - avoid tight polling loops;
    - wake periodically to discover newly configured sensors;
    - stop cleanly during application shutdown.

    Individual sensor hardware failures are already isolated by
    HardwareSensorPollingRuntime. This worker deals only with
    cycle-level failures such as temporary database errors.
    """

    def __init__(
        self,
        *,
        session_factory: Callable[
            [],
            AsyncSession,
        ],
        polling_runtime: (
            HardwareSensorPollingRuntime
        ),
        discovery_interval_seconds: (
            float
        ) = 5.0,
        clock: Callable[
            [],
            datetime,
        ] = _utc_now,
    ) -> None:
        if (
            discovery_interval_seconds
            <= 0
        ):
            raise HardwareSensorWorkerError(
                "Sensor discovery interval "
                "must be greater than zero"
            )

        self._session_factory = (
            session_factory
        )

        self._polling_runtime = (
            polling_runtime
        )

        self._discovery_interval_seconds = (
            float(
                discovery_interval_seconds
            )
        )

        self._clock = clock

        self._stop_event = (
            asyncio.Event()
        )

        self._task: (
            asyncio.Task[None]
            | None
        ) = None

        self._last_result: (
            HardwareSensorPollingCycleResult
            | None
        ) = None

        self._last_error: (
            Exception | None
        ) = None

    # ========================================================
    # STATE
    # ========================================================

    @property
    def running(
        self,
    ) -> bool:
        return (
            self._task is not None
            and not self._task.done()
        )

    @property
    def last_result(
        self,
    ) -> (
        HardwareSensorPollingCycleResult
        | None
    ):
        return self._last_result

    @property
    def last_error(
        self,
    ) -> Exception | None:
        return self._last_error

    # ========================================================
    # SINGLE CYCLE
    # ========================================================

    async def run_once(
        self,
        *,
        current_time: (
            datetime | None
        ) = None,
    ) -> HardwareSensorPollingCycleResult:
        """
        Execute exactly one polling cycle using a fresh
        database session.
        """

        cycle_time = (
            current_time
            or self._clock()
        )

        if (
            cycle_time.tzinfo is None
            or cycle_time.utcoffset()
            is None
        ):
            raise HardwareSensorWorkerError(
                "Sensor worker clock must return "
                "a timezone-aware datetime"
            )

        async with (
            self._session_factory()
        ) as session:
            result = (
                await self
                ._polling_runtime
                .run_cycle(
                    session,
                    current_time=cycle_time,
                )
            )

        self._last_result = (
            result
        )

        self._last_error = None

        return result

    # ========================================================
    # SLEEP CALCULATION
    # ========================================================

    def _calculate_sleep_seconds(
        self,
        *,
        current_time: datetime,
    ) -> float:
        """
        Sleep until the next known sensor is due, but never
        longer than the discovery interval.

        The discovery ceiling ensures that newly created,
        enabled, or reconfigured Sensor records are noticed
        without requiring an application restart.
        """

        next_due = (
            self._polling_runtime
            .next_scheduled_at()
        )

        if next_due is None:
            return (
                self._discovery_interval_seconds
            )

        if next_due.tzinfo is None:
            # SQLite-derived datetimes should not normally
            # reach the in-memory runtime schedule, but protect
            # the worker from accidental naive values.
            next_due = next_due.replace(
                tzinfo=timezone.utc
            )

        seconds_until_due = (
            next_due
            - current_time
        ).total_seconds()

        if seconds_until_due <= 0:
            return 0.0

        return min(
            seconds_until_due,
            self._discovery_interval_seconds,
        )

    # ========================================================
    # BACKGROUND LOOP
    # ========================================================

    async def _run(
        self,
    ) -> None:
        while not (
            self._stop_event.is_set()
        ):
            cycle_time = self._clock()

            try:
                await self.run_once(
                    current_time=cycle_time,
                )

            except asyncio.CancelledError:
                raise

            except Exception as exc:
                # Individual hardware sensor failures should
                # already be represented in polling results.
                #
                # Reaching here usually indicates a cycle-level
                # infrastructure problem such as temporary DB
                # failure. Keep the worker alive so it can
                # recover on the next cycle.
                self._last_error = exc

                logger.exception(
                    "Hardware sensor polling "
                    "cycle failed"
                )

            if (
                self._stop_event.is_set()
            ):
                break

            sleep_seconds = (
                self._calculate_sleep_seconds(
                    current_time=(
                        self._clock()
                    ),
                )
            )

            # Avoid a CPU-spin if a due time lands exactly at
            # the current clock value.
            if sleep_seconds <= 0:
                await asyncio.sleep(0)

                continue

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=sleep_seconds,
                )

            except TimeoutError:
                # Normal wake-up for the next polling cycle.
                pass

    # ========================================================
    # START
    # ========================================================

    async def start(
        self,
    ) -> None:
        """
        Start the worker.

        Calling start repeatedly while already running is safe.
        """

        if self.running:
            return

        self._stop_event.clear()

        self._task = (
            asyncio.create_task(
                self._run(),
                name=(
                    "aquamind-hardware-"
                    "sensor-worker"
                ),
            )
        )

        # Give the task one event-loop turn so startup problems
        # that occur immediately are observable during tests and
        # application initialization.
        await asyncio.sleep(0)

    # ========================================================
    # STOP
    # ========================================================

    async def stop(
        self,
    ) -> None:
        """
        Request graceful shutdown and wait for the worker.

        Calling stop when the worker is not running is safe.
        """

        task = self._task

        if task is None:
            return

        self._stop_event.set()

        try:
            await task

        finally:
            self._task = None