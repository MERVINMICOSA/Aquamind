from __future__ import annotations

import pytest

from app.hardware.ds18b20_reader import (
    DS18B20Reader,
)
from app.hardware.sensor_runtime import (
    HardwareSensorRuntime,
    build_hardware_sensor_runtime,
)
from app.services.hardware_sensor_polling_service import (
    HardwareSensorPollingRuntime,
)
from app.services.hardware_sensor_worker import (
    HardwareSensorWorker,
    HardwareSensorWorkerError,
)


# ============================================================
# FIXED VALUES
# ============================================================


DEVICE_ID = "28-00000abcdef0"


# ============================================================
# SESSION FACTORY
# ============================================================


def unused_session_factory():
    """
    Composition tests do not execute a database cycle.
    """

    raise AssertionError(
        "Session factory must not be used "
        "while merely building the runtime"
    )


# ============================================================
# COMPOSITION
# ============================================================


def test_builds_complete_sensor_runtime():
    runtime = (
        build_hardware_sensor_runtime(
            session_factory=(
                unused_session_factory
            )
        )
    )

    assert isinstance(
        runtime,
        HardwareSensorRuntime,
    )

    assert isinstance(
        runtime.ds18b20_reader,
        DS18B20Reader,
    )

    assert isinstance(
        runtime.polling_runtime,
        HardwareSensorPollingRuntime,
    )

    assert isinstance(
        runtime.worker,
        HardwareSensorWorker,
    )

    assert (
        runtime.worker.running
        is False
    )


# ============================================================
# IDENTIFIER ROUTING
# ============================================================


def test_runtime_registers_ds18b20_reader():
    runtime = (
        build_hardware_sensor_runtime(
            session_factory=(
                unused_session_factory
            )
        )
    )

    reader = (
        runtime
        .reader_registry
        .resolve(
            DEVICE_ID
        )
    )

    assert (
        reader
        is runtime.ds18b20_reader
    )


def test_runtime_does_not_guess_unknown_sensor_adapter():
    runtime = (
        build_hardware_sensor_runtime(
            session_factory=(
                unused_session_factory
            )
        )
    )

    assert (
        runtime
        .reader_registry
        .resolve(
            "unknown-physical-device"
        )
        is None
    )


# ============================================================
# REAL DS18B20 FILESYSTEM COMPOSITION
# ============================================================


def test_custom_ds18b20_root_is_used(
    tmp_path,
):
    device_directory = (
        tmp_path
        / DEVICE_ID
    )

    device_directory.mkdir()

    (
        device_directory
        / "w1_slave"
    ).write_text(
        (
            "73 01 4b 46 7f ff 0d 10 41 "
            ": crc=41 YES\n"
            "73 01 4b 46 7f ff 0d 10 41 "
            "t=21375\n"
        ),
        encoding="utf-8",
    )

    runtime = (
        build_hardware_sensor_runtime(
            session_factory=(
                unused_session_factory
            ),
            ds18b20_devices_root=(
                tmp_path
            ),
        )
    )

    reader = (
        runtime
        .reader_registry
        .resolve(
            DEVICE_ID
        )
    )

    assert reader is not None

    reading = reader.read(
        DEVICE_ID
    )

    assert (
        reading.hardware_identifier
        == DEVICE_ID
    )

    assert (
        reading.value_numeric
        == pytest.approx(
            21.375
        )
    )


# ============================================================
# WORKER CONFIGURATION
# ============================================================


def test_invalid_discovery_interval_is_rejected():
    with pytest.raises(
        HardwareSensorWorkerError,
        match=(
            "discovery interval "
            "must be greater than zero"
        ),
    ):
        build_hardware_sensor_runtime(
            session_factory=(
                unused_session_factory
            ),
            discovery_interval_seconds=0,
        )