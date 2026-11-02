from __future__ import annotations

import asyncio
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace

import pytest

from app.services.hardware_sensor_worker import (
    HardwareSensorWorker,
    HardwareSensorWorkerError,
)


pytestmark = pytest.mark.asyncio


NOW = datetime(
    2026,
    9,
    4,
    8,
    0,
    0,
    tzinfo=timezone.utc,
)


# ============================================================
# FAKE SESSION
# ============================================================


class FakeSession:
    def __init__(
        self,
        number,
    ):
        self.number = number
        self.entered = False
        self.exited = False

    async def __aenter__(
        self,
    ):
        self.entered = True

        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        self.exited = True


class FakeSessionFactory:
    def __init__(
        self,
    ):
        self.sessions = []

    def __call__(
        self,
    ):
        session = FakeSession(
            len(
                self.sessions
            )
            + 1
        )

        self.sessions.append(
            session
        )

        return session


# ============================================================
# FAKE RUNTIME
# ============================================================


class FakePollingRuntime:
    def __init__(
        self,
    ):
        self.calls = []
        self.next_due = None
        self.failures_remaining = 0

    async def run_cycle(
        self,
        session,
        *,
        current_time,
    ):
        self.calls.append(
            (
                session,
                current_time,
            )
        )

        if (
            self.failures_remaining
            > 0
        ):
            self.failures_remaining -= 1

            raise RuntimeError(
                "Temporary polling failure"
            )

        return SimpleNamespace(
            started_at=current_time,
            sensor_results=(),
        )

    def next_scheduled_at(
        self,
    ):
        return self.next_due


# ============================================================
# ONE CYCLE / SESSION LIFETIME
# ============================================================


async def test_run_once_uses_fresh_session():
    session_factory = (
        FakeSessionFactory()
    )

    runtime = (
        FakePollingRuntime()
    )

    worker = HardwareSensorWorker(
        session_factory=(
            session_factory
        ),
        polling_runtime=runtime,
        clock=lambda: NOW,
    )

    result = await worker.run_once()

    assert (
        result.started_at
        == NOW
    )

    assert (
        len(
            session_factory.sessions
        )
        == 1
    )

    session = (
        session_factory.sessions[0]
    )

    assert session.entered is True
    assert session.exited is True

    assert (
        runtime.calls[0][0]
        is session
    )


async def test_multiple_cycles_use_different_sessions():
    session_factory = (
        FakeSessionFactory()
    )

    runtime = (
        FakePollingRuntime()
    )

    worker = HardwareSensorWorker(
        session_factory=(
            session_factory
        ),
        polling_runtime=runtime,
        clock=lambda: NOW,
    )

    await worker.run_once()

    await worker.run_once(
        current_time=(
            NOW
            + timedelta(
                seconds=30
            )
        )
    )

    assert (
        len(
            session_factory.sessions
        )
        == 2
    )

    assert (
        session_factory.sessions[0]
        is not
        session_factory.sessions[1]
    )

    assert all(
        session.exited
        for session
        in session_factory.sessions
    )


# ============================================================
# CLOCK VALIDATION
# ============================================================


async def test_worker_requires_timezone_aware_time():
    worker = HardwareSensorWorker(
        session_factory=(
            FakeSessionFactory()
        ),
        polling_runtime=(
            FakePollingRuntime()
        ),
        clock=lambda: datetime(
            2026,
            9,
            4,
            8,
            0,
            0,
        ),
    )

    with pytest.raises(
        HardwareSensorWorkerError,
        match=(
            "timezone-aware"
        ),
    ):
        await worker.run_once()


# ============================================================
# EFFICIENT WAKE TIME
# ============================================================


async def test_worker_sleeps_until_earlier_next_due():
    runtime = (
        FakePollingRuntime()
    )

    runtime.next_due = (
        NOW
        + timedelta(
            seconds=2
        )
    )

    worker = HardwareSensorWorker(
        session_factory=(
            FakeSessionFactory()
        ),
        polling_runtime=runtime,
        discovery_interval_seconds=5,
        clock=lambda: NOW,
    )

    assert (
        worker._calculate_sleep_seconds(
            current_time=NOW,
        )
        == pytest.approx(
            2.0
        )
    )


async def test_discovery_interval_caps_sleep():
    runtime = (
        FakePollingRuntime()
    )

    runtime.next_due = (
        NOW
        + timedelta(
            seconds=60
        )
    )

    worker = HardwareSensorWorker(
        session_factory=(
            FakeSessionFactory()
        ),
        polling_runtime=runtime,
        discovery_interval_seconds=5,
        clock=lambda: NOW,
    )

    assert (
        worker._calculate_sleep_seconds(
            current_time=NOW,
        )
        == pytest.approx(
            5.0
        )
    )


# ============================================================
# START / STOP
# ============================================================


async def test_worker_starts_and_stops_cleanly():
    session_factory = (
        FakeSessionFactory()
    )

    runtime = (
        FakePollingRuntime()
    )

    worker = HardwareSensorWorker(
        session_factory=(
            session_factory
        ),
        polling_runtime=runtime,
        discovery_interval_seconds=(
            0.01
        ),
        clock=lambda: NOW,
    )

    assert worker.running is False

    await worker.start()

    assert worker.running is True

    # Allow at least one cycle to execute.
    await asyncio.sleep(
        0.02
    )

    await worker.stop()

    assert worker.running is False

    assert (
        len(
            runtime.calls
        )
        >= 1
    )


# ============================================================
# TRANSIENT FAILURE RECOVERY
# ============================================================


async def test_worker_survives_cycle_failure():
    session_factory = (
        FakeSessionFactory()
    )

    runtime = (
        FakePollingRuntime()
    )

    runtime.failures_remaining = 1

    worker = HardwareSensorWorker(
        session_factory=(
            session_factory
        ),
        polling_runtime=runtime,
        discovery_interval_seconds=(
            0.01
        ),
        clock=lambda: NOW,
    )

    await worker.start()

    await asyncio.sleep(
        0.04
    )

    await worker.stop()

    # First cycle failed, but the worker continued and made
    # another attempt.
    assert (
        len(
            runtime.calls
        )
        >= 2
    )

    assert (
        worker.last_result
        is not None
    )

    assert (
        worker.last_error
        is None
    )