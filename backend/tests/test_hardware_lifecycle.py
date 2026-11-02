from __future__ import annotations

import pytest

import app.main as main_module


pytestmark = pytest.mark.asyncio


# ============================================================
# EXECUTOR ATTACH / DETACH
# ============================================================


async def test_lifespan_attaches_and_closes_hardware_executor(
    monkeypatch,
):
    calls = []

    class FakeExecutor:
        pass

    executor = FakeExecutor()

    async def fake_build(
        settings,
    ):
        calls.append(
            "build"
        )

        return executor

    async def fake_shutdown(
        received_executor,
    ):
        assert (
            received_executor
            is executor
        )

        calls.append(
            "shutdown"
        )

    monkeypatch.setattr(
        main_module,
        "build_hardware_actuator_executor",
        fake_build,
    )

    monkeypatch.setattr(
        main_module,
        "shutdown_hardware_actuator_executor",
        fake_shutdown,
    )

    async with main_module.lifespan(
        main_module.app
    ):
        assert (
            main_module.app.state
            .actuator_executor
            is executor
        )

        assert calls == [
            "build"
        ]

    assert (
        main_module.app.state
        .actuator_executor
        is None
    )

    assert calls == [
        "build",
        "shutdown",
    ]


# ============================================================
# DISABLED HARDWARE
# ============================================================


async def test_lifespan_supports_disabled_hardware(
    monkeypatch,
):
    calls = []

    async def fake_build(
        settings,
    ):
        calls.append(
            "build"
        )

        return None

    async def fake_shutdown(
        executor,
    ):
        assert executor is None

        calls.append(
            "shutdown"
        )

    monkeypatch.setattr(
        main_module,
        "build_hardware_actuator_executor",
        fake_build,
    )

    monkeypatch.setattr(
        main_module,
        "shutdown_hardware_actuator_executor",
        fake_shutdown,
    )

    async with main_module.lifespan(
        main_module.app
    ):
        assert (
            main_module.app.state
            .actuator_executor
            is None
        )

    assert calls == [
        "build",
        "shutdown",
    ]


# ============================================================
# STARTUP FAILURE
# ============================================================


async def test_hardware_startup_failure_is_not_silenced(
    monkeypatch,
):
    async def failing_build(
        settings,
    ):
        raise RuntimeError(
            "Hardware startup failed"
        )

    monkeypatch.setattr(
        main_module,
        "build_hardware_actuator_executor",
        failing_build,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Hardware startup failed"
        ),
    ):
        async with main_module.lifespan(
            main_module.app
        ):
            pass

    assert (
        main_module.app.state
        .actuator_executor
        is None
    )