from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.enums import (
    LocationType,
    MeasurementType,
    SensorType,
)
from app.hardware.sensor_reader import (
    HardwareSensorReadError,
)
from app.models.sensors import (
    Sensor,
)
from app.models.system import (
    AquaponicsSystem,
)
from app.services import (
    hardware_sensor_polling_service
    as polling_service,
)
from app.services.hardware_sensor_polling_service import (
    HardwareSensorPollingError,
    HardwareSensorPollingOutcome,
    HardwareSensorPollingRuntime,
)
from app.hardware.sensor_registry import (
    HardwareSensorReaderRegistry,
    HardwareSensorReaderRoute,
)
from app.hardware.ds18b20_reader import (
    DS18B20Reader,
)

pytestmark = pytest.mark.asyncio


# ============================================================
# TIME
# ============================================================


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
# READER
# ============================================================


class DummyReader:
    def read(
        self,
        hardware_identifier,
    ):
        raise AssertionError(
            "Polling tests patch the acquisition "
            "boundary directly"
        )


# ============================================================
# DATABASE HELPERS
# ============================================================


async def create_system(
    session,
):
    system = AquaponicsSystem(
        name="Polling System",
    )

    session.add(
        system
    )

    await session.commit()
    await session.refresh(
        system
    )

    return system


async def create_sensor(
    session,
    system,
    *,
    name,
    sensor_type=(
        SensorType.WATER_TEMPERATURE
    ),
    measurement_type=(
        MeasurementType.TEMPERATURE
    ),
    hardware_identifier=None,
    sampling_interval_seconds=30,
    is_enabled=True,
    is_simulated=False,
):
    sensor = Sensor(
        system_id=system.id,
        name=name,
        sensor_type=sensor_type,
        measurement_type=(
            measurement_type
        ),
        location_type=(
            LocationType.SYSTEM
        ),
        location_id=None,
        unit="C",
        hardware_identifier=(
            hardware_identifier
            or f"hardware-{uuid4()}"
        ),
        is_simulated=(
            is_simulated
        ),
        is_enabled=(
            is_enabled
        ),
        sampling_interval_seconds=(
            sampling_interval_seconds
        ),
    )

    session.add(
        sensor
    )

    await session.commit()
    await session.refresh(
        sensor
    )

    return sensor


def create_runtime():
    return HardwareSensorPollingRuntime(
        reader_registry=(
            HardwareSensorReaderRegistry(
                [
                    HardwareSensorReaderRoute(
                        name=(
                            "test-physical-reader"
                        ),
                        matches=(
                            lambda identifier:
                            identifier.startswith(
                                "hardware-"
                            )
                        ),
                        reader=DummyReader(),
                    ),
                ]
            )
        )
    )


# ============================================================
# FIRST ACQUISITION
# ============================================================


async def test_new_physical_sensor_is_due_immediately(
    test_session,
    monkeypatch,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
        name="Water Temperature",
    )

    calls = []

    reading_id = uuid4()

    async def fake_acquire(
        session,
        *,
        sensor_id,
        reader,
        actuator_executor=None,
    ):
        calls.append(
            sensor_id
        )

        return SimpleNamespace(
            id=reading_id
        )

    monkeypatch.setattr(
        polling_service,
        "acquire_hardware_sensor_reading",
        fake_acquire,
    )

    runtime = create_runtime()

    result = await runtime.run_cycle(
        test_session,
        current_time=NOW,
    )

    assert calls == [
        sensor.id
    ]

    assert (
        result.attempted_count
        == 1
    )

    assert (
        result.acquired_count
        == 1
    )

    assert (
        result.sensor_results[
            0
        ].outcome
        == HardwareSensorPollingOutcome.ACQUIRED
    )

    assert (
        result.sensor_results[
            0
        ].reading_id
        == reading_id
    )

    assert (
        runtime.next_due_at(
            sensor.id
        )
        == NOW
        + timedelta(
            seconds=30
        )
    )


# ============================================================
# SAMPLING INTERVAL
# ============================================================


async def test_sensor_is_not_polled_before_sampling_interval(
    test_session,
    monkeypatch,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
        name="Water Temperature",
        sampling_interval_seconds=30,
    )

    calls = []

    async def fake_acquire(
        session,
        *,
        sensor_id,
        reader,
        actuator_executor=None,
    ):
        calls.append(
            sensor_id
        )

        return SimpleNamespace(
            id=uuid4()
        )

    monkeypatch.setattr(
        polling_service,
        "acquire_hardware_sensor_reading",
        fake_acquire,
    )

    runtime = create_runtime()

    await runtime.run_cycle(
        test_session,
        current_time=NOW,
    )

    second = await runtime.run_cycle(
        test_session,
        current_time=(
            NOW
            + timedelta(
                seconds=29
            )
        ),
    )

    assert calls == [
        sensor.id
    ]

    assert (
        second.attempted_count
        == 0
    )


async def test_sensor_is_polled_again_when_interval_is_due(
    test_session,
    monkeypatch,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
        name="Water Temperature",
        sampling_interval_seconds=30,
    )

    calls = []

    async def fake_acquire(
        session,
        *,
        sensor_id,
        reader,
        actuator_executor=None,
    ):
        calls.append(
            sensor_id
        )

        return SimpleNamespace(
            id=uuid4()
        )

    monkeypatch.setattr(
        polling_service,
        "acquire_hardware_sensor_reading",
        fake_acquire,
    )

    runtime = create_runtime()

    await runtime.run_cycle(
        test_session,
        current_time=NOW,
    )

    result = await runtime.run_cycle(
        test_session,
        current_time=(
            NOW
            + timedelta(
                seconds=30
            )
        ),
    )

    assert calls == [
        sensor.id,
        sensor.id,
    ]

    assert (
        result.acquired_count
        == 1
    )


# ============================================================
# UNSUPPORTED SENSOR
# ============================================================


async def test_sensor_without_registered_reader_is_isolated(
    test_session,
    monkeypatch,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
        name="Physical pH",
        sensor_type=(
            SensorType.PH
        ),
        measurement_type=(
            MeasurementType.PH
        ),
        hardware_identifier=(
            "unsupported-device"
        ),
    )

    async def acquisition_must_not_run(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Unsupported sensor must not "
            "reach acquisition"
        )

    monkeypatch.setattr(
        polling_service,
        "acquire_hardware_sensor_reading",
        acquisition_must_not_run,
    )

    runtime = create_runtime()

    result = await runtime.run_cycle(
        test_session,
        current_time=NOW,
    )

    assert (
        result.unsupported_count
        == 1
    )

    item = (
        result.sensor_results[0]
    )

    assert (
        item.sensor_id
        == sensor.id
    )

    assert (
        item.outcome
        == HardwareSensorPollingOutcome.UNSUPPORTED
    )

    assert (
        item.fault_code
        == "unsupported_sensor_reader"
    )


# ============================================================
# FAILURE ISOLATION
# ============================================================


async def test_one_hardware_failure_does_not_block_another_sensor(
    test_session,
    monkeypatch,
):
    system = await create_system(
        test_session
    )

    first = await create_sensor(
        test_session,
        system,
        name="Temperature A",
    )

    second = await create_sensor(
        test_session,
        system,
        name="Temperature B",
    )

    successful_reading_id = (
        uuid4()
    )

    async def fake_acquire(
        session,
        *,
        sensor_id,
        reader,
        actuator_executor=None,
    ):
        if sensor_id == first.id:
            raise HardwareSensorReadError(
                "1-Wire device unavailable",
                fault_code=(
                    "sensor_not_found"
                ),
            )

        return SimpleNamespace(
            id=(
                successful_reading_id
            )
        )

    monkeypatch.setattr(
        polling_service,
        "acquire_hardware_sensor_reading",
        fake_acquire,
    )

    runtime = create_runtime()

    result = await runtime.run_cycle(
        test_session,
        current_time=NOW,
    )

    by_sensor = {
        item.sensor_id: item
        for item in (
            result.sensor_results
        )
    }

    assert (
        by_sensor[
            first.id
        ].outcome
        == HardwareSensorPollingOutcome.FAILED
    )

    assert (
        by_sensor[
            first.id
        ].fault_code
        == "sensor_not_found"
    )

    assert (
        by_sensor[
            second.id
        ].outcome
        == HardwareSensorPollingOutcome.ACQUIRED
    )

    assert (
        by_sensor[
            second.id
        ].reading_id
        == successful_reading_id
    )

    assert (
        result.failed_count
        == 1
    )

    assert (
        result.acquired_count
        == 1
    )


# ============================================================
# NON-PHYSICAL SENSOR FILTERING
# ============================================================


async def test_disabled_and_simulated_sensors_are_not_polled(
    test_session,
    monkeypatch,
):
    system = await create_system(
        test_session
    )

    await create_sensor(
        test_session,
        system,
        name="Disabled Sensor",
        is_enabled=False,
    )

    await create_sensor(
        test_session,
        system,
        name="Simulated Sensor",
        is_simulated=True,
    )

    async def acquisition_must_not_run(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Non-physical sensors must "
            "not be polled"
        )

    monkeypatch.setattr(
        polling_service,
        "acquire_hardware_sensor_reading",
        acquisition_must_not_run,
    )

    runtime = create_runtime()

    result = await runtime.run_cycle(
        test_session,
        current_time=NOW,
    )

    assert (
        result.attempted_count
        == 0
    )


# ============================================================
# CLOCK SAFETY
# ============================================================


async def test_polling_requires_timezone_aware_time(
    test_session,
):
    runtime = create_runtime()

    with pytest.raises(
        HardwareSensorPollingError,
        match=(
            "timezone-aware"
        ),
    ):
        await runtime.run_cycle(
            test_session,
            current_time=datetime(
                2026,
                9,
                4,
                8,
                0,
                0,
            ),
        )

async def test_air_temperature_sensor_can_use_identifier_routed_reader(
    test_session,
    monkeypatch,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
        name="Air Temperature",
        sensor_type=(
            SensorType.AIR_TEMPERATURE
        ),
        measurement_type=(
            MeasurementType.TEMPERATURE
        ),
        hardware_identifier=(
            "28-00000abcdef0"
        ),
    )

    reader = DummyReader()

    registry = (
        HardwareSensorReaderRegistry(
            [
                HardwareSensorReaderRoute(
                    name="ds18b20",
                    matches=(
                        DS18B20Reader
                        .supports_identifier
                    ),
                    reader=reader,
                ),
            ]
        )
    )

    runtime = (
        HardwareSensorPollingRuntime(
            reader_registry=registry
        )
    )

    acquired = []

    async def fake_acquire(
        session,
        *,
        sensor_id,
        reader,
        actuator_executor=None,
    ):
        acquired.append(
            (
                sensor_id,
                reader,
            )
        )

        return SimpleNamespace(
            id=uuid4()
        )

    monkeypatch.setattr(
        polling_service,
        "acquire_hardware_sensor_reading",
        fake_acquire,
    )

    result = await runtime.run_cycle(
        test_session,
        current_time=NOW,
    )

    assert acquired == [
        (
            sensor.id,
            reader,
        )
    ]

    assert (
        result.acquired_count
        == 1
    )