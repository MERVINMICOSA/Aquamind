from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI

import app.main as main_module


pytestmark = pytest.mark.asyncio


# ============================================================
# TEST WORKER
# ============================================================


class RecordingWorker:
    def __init__(
        self,
        events,
        *,
        start_error=None,
    ):
        self.events = events
        self.start_error = start_error

        self.started = False
        self.stopped = False

    async def start(
        self,
    ):
        self.events.append(
            "sensor_start"
        )

        if self.start_error is not None:
            raise self.start_error

        self.started = True

    async def stop(
        self,
    ):
        self.events.append(
            "sensor_stop"
        )

        self.stopped = True


# ============================================================
# HARDWARE DISABLED
# ============================================================


async def test_sensor_runtime_is_not_started_when_hardware_disabled(
    monkeypatch,
):
    events = []

    monkeypatch.setattr(
        main_module.settings,
        "HARDWARE_ENABLED",
        False,
    )

    async def fake_build_executor(
        settings,
    ):
        events.append(
            "actuator_build"
        )

        return None

    async def fake_shutdown_executor(
        executor,
    ):
        events.append(
            "actuator_shutdown"
        )

    def sensor_runtime_must_not_build(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Sensor runtime must not be built "
            "while hardware is disabled"
        )

    monkeypatch.setattr(
        main_module,
        "build_hardware_actuator_executor",
        fake_build_executor,
    )

    monkeypatch.setattr(
        main_module,
        "shutdown_hardware_actuator_executor",
        fake_shutdown_executor,
    )

    monkeypatch.setattr(
        main_module,
        "build_hardware_sensor_runtime",
        sensor_runtime_must_not_build,
    )

    test_app = FastAPI()

    async with main_module.lifespan(
        test_app
    ):
        assert (
            test_app.state.actuator_executor
            is None
        )

        assert (
            test_app.state.hardware_sensor_runtime
            is None
        )

    assert events == [
        "actuator_build",
        "actuator_shutdown",
    ]


# ============================================================
# HARDWARE ENABLED
# ============================================================


async def test_sensor_runtime_starts_with_actuator_executor(
    monkeypatch,
):
    events = []

    executor = object()

    worker = RecordingWorker(
        events
    )

    sensor_runtime = (
        SimpleNamespace(
            worker=worker
        )
    )

    captured = {}

    monkeypatch.setattr(
        main_module.settings,
        "HARDWARE_ENABLED",
        True,
    )

    async def fake_build_executor(
        settings,
    ):
        events.append(
            "actuator_build"
        )

        return executor

    def fake_build_sensor_runtime(
        *,
        session_factory,
        actuator_executor=None,
        **kwargs,
    ):
        events.append(
            "sensor_build"
        )

        captured[
            "session_factory"
        ] = session_factory

        captured[
            "actuator_executor"
        ] = actuator_executor

        return sensor_runtime

    async def fake_shutdown_executor(
        received_executor,
    ):
        assert (
            received_executor
            is executor
        )

        events.append(
            "actuator_shutdown"
        )

    monkeypatch.setattr(
        main_module,
        "build_hardware_actuator_executor",
        fake_build_executor,
    )

    monkeypatch.setattr(
        main_module,
        "build_hardware_sensor_runtime",
        fake_build_sensor_runtime,
    )

    monkeypatch.setattr(
        main_module,
        "shutdown_hardware_actuator_executor",
        fake_shutdown_executor,
    )

    test_app = FastAPI()

    async with main_module.lifespan(
        test_app
    ):
        assert (
            test_app.state.actuator_executor
            is executor
        )

        assert (
            test_app.state.hardware_sensor_runtime
            is sensor_runtime
        )

        assert worker.started is True

        assert (
            captured[
                "session_factory"
            ]
            is main_module.SessionFactory
        )

        assert (
            captured[
                "actuator_executor"
            ]
            is executor
        )

    assert worker.stopped is True

    assert (
        test_app.state.hardware_sensor_runtime
        is None
    )

    assert (
        test_app.state.actuator_executor
        is None
    )

    assert events == [
        "actuator_build",
        "sensor_build",
        "sensor_start",
        "sensor_stop",
        "actuator_shutdown",
    ]


# ============================================================
# SENSOR STARTUP FAILURE
# ============================================================


async def test_sensor_startup_failure_cleans_up_actuator_hardware(
    monkeypatch,
):
    events = []

    executor = object()

    startup_error = RuntimeError(
        "Sensor worker failed to start"
    )

    worker = RecordingWorker(
        events,
        start_error=startup_error,
    )

    sensor_runtime = (
        SimpleNamespace(
            worker=worker
        )
    )

    monkeypatch.setattr(
        main_module.settings,
        "HARDWARE_ENABLED",
        True,
    )

    async def fake_build_executor(
        settings,
    ):
        events.append(
            "actuator_build"
        )

        return executor

    def fake_build_sensor_runtime(
        **kwargs,
    ):
        events.append(
            "sensor_build"
        )

        return sensor_runtime

    async def fake_shutdown_executor(
        received_executor,
    ):
        assert (
            received_executor
            is executor
        )

        events.append(
            "actuator_shutdown"
        )

    monkeypatch.setattr(
        main_module,
        "build_hardware_actuator_executor",
        fake_build_executor,
    )

    monkeypatch.setattr(
        main_module,
        "build_hardware_sensor_runtime",
        fake_build_sensor_runtime,
    )

    monkeypatch.setattr(
        main_module,
        "shutdown_hardware_actuator_executor",
        fake_shutdown_executor,
    )

    test_app = FastAPI()

    with pytest.raises(
        RuntimeError,
        match=(
            "Sensor worker failed to start"
        ),
    ):
        async with main_module.lifespan(
            test_app
        ):
            raise AssertionError(
                "Application must not enter "
                "running state"
            )

    assert (
        test_app.state.hardware_sensor_runtime
        is None
    )

    assert (
        test_app.state.actuator_executor
        is None
    )

    assert events == [
        "actuator_build",
        "sensor_build",
        "sensor_start",
        "sensor_stop",
        "actuator_shutdown",
    ]


# ============================================================
# ACTUATOR STARTUP FAILURE
# ============================================================


async def test_actuator_startup_failure_does_not_start_sensor_runtime(
    monkeypatch,
):
    events = []

    startup_error = RuntimeError(
        "Actuator hardware failed"
    )

    monkeypatch.setattr(
        main_module.settings,
        "HARDWARE_ENABLED",
        True,
    )

    async def fake_build_executor(
        settings,
    ):
        events.append(
            "actuator_build"
        )

        raise startup_error

    def sensor_runtime_must_not_build(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Sensor runtime must not start "
            "after actuator startup failure"
        )

    async def fake_shutdown_executor(
        executor,
    ):
        assert executor is None

        events.append(
            "actuator_shutdown"
        )

    monkeypatch.setattr(
        main_module,
        "build_hardware_actuator_executor",
        fake_build_executor,
    )

    monkeypatch.setattr(
        main_module,
        "build_hardware_sensor_runtime",
        sensor_runtime_must_not_build,
    )

    monkeypatch.setattr(
        main_module,
        "shutdown_hardware_actuator_executor",
        fake_shutdown_executor,
    )

    test_app = FastAPI()

    with pytest.raises(
        RuntimeError,
        match=(
            "Actuator hardware failed"
        ),
    ):
        async with main_module.lifespan(
            test_app
        ):
            raise AssertionError(
                "Application must not start"
            )

    assert (
        test_app.state.hardware_sensor_runtime
        is None
    )

    assert (
        test_app.state.actuator_executor
        is None
    )

    assert events == [
        "actuator_build",
        "actuator_shutdown",
    ]