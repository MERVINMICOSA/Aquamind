from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

import pytest
from sqlalchemy import select

from app.db.enums import (
    LocationType,
    MeasurementType,
    ReadingQuality,
    ReadingSource,
    SensorType,
)
from app.hardware.sensor_reader import (
    HardwareSensorReading,
)
from app.models.sensors import (
    Sensor,
    SensorReading,
)
from app.models.system import (
    AquaponicsSystem,
)
from app.services import (
    hardware_sensor_acquisition_service
    as acquisition_service,
)
from app.services.hardware_sensor_acquisition_service import (
    HardwareSensorAcquisitionError,
    acquire_hardware_sensor_reading,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# FIXED VALUES
# ============================================================


DEVICE_ID = "28-00000abcdef0"

RECORDED_AT = datetime(
    2026,
    9,
    4,
    7,
    0,
    0,
    tzinfo=timezone.utc,
)


# ============================================================
# READER
# ============================================================


class RecordingReader:
    def __init__(
        self,
        *,
        result=None,
    ):
        self.identifiers = []

        self.result = (
            result
            or HardwareSensorReading(
                hardware_identifier=(
                    DEVICE_ID
                ),
                value_numeric=23.5,
                recorded_at=RECORDED_AT,
            )
        )

    def read(
        self,
        hardware_identifier,
    ):
        self.identifiers.append(
            hardware_identifier
        )

        return self.result


# ============================================================
# DATABASE HELPERS
# ============================================================


async def create_system(
    session,
):
    system = AquaponicsSystem(
        name=(
            "Hardware Sensor System"
        ),
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
    hardware_identifier=DEVICE_ID,
    is_simulated=False,
    is_enabled=True,
):
    sensor = Sensor(
        system_id=system.id,
        name=(
            "Physical Temperature Sensor"
        ),
        sensor_type=next(
            iter(
                SensorType
            )
        ),
        measurement_type=next(
            iter(
                MeasurementType
            )
        ),
        location_type=next(
            iter(
                LocationType
            )
        ),
        location_id=None,
        unit="C",
        hardware_identifier=(
            hardware_identifier
        ),
        is_simulated=(
            is_simulated
        ),
        is_enabled=(
            is_enabled
        ),
        sampling_interval_seconds=30,
    )

    session.add(
        sensor
    )

    await session.commit()
    await session.refresh(
        sensor
    )

    return sensor


async def get_sensor_readings(
    session,
    sensor,
):
    result = await session.execute(
        select(
            SensorReading
        ).where(
            SensorReading.sensor_id
            == sensor.id
        )
    )

    return list(
        result.scalars().all()
    )


# ============================================================
# SUCCESS
# ============================================================


async def test_successful_hardware_read_is_persisted(
    test_session,
    monkeypatch,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    reader = RecordingReader()

    downstream = []

    async def fake_alert(
        session,
        reading,
    ):
        persisted = await session.get(
            SensorReading,
            reading.id,
        )

        assert persisted is not None

        downstream.append(
            "alert"
        )

        return None

    async def automation_must_not_run(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Automation must not run "
            "without an executor"
        )

    monkeypatch.setattr(
        acquisition_service,
        "process_sensor_reading",
        fake_alert,
    )

    monkeypatch.setattr(
        acquisition_service,
        "process_sensor_reading_automation",
        automation_must_not_run,
    )

    reading = (
        await acquire_hardware_sensor_reading(
            test_session,
            sensor_id=sensor.id,
            reader=reader,
            actuator_executor=None,
        )
    )

    assert reader.identifiers == [
        DEVICE_ID
    ]

    assert (
        float(
            reading.value_numeric
        )
        == pytest.approx(
            23.5
        )
    )

    assert (
        reading.recorded_at
        == RECORDED_AT
        or reading.recorded_at.replace(
            tzinfo=timezone.utc
        )
        == RECORDED_AT
    )

    assert (
        reading.quality_status
        == ReadingQuality.GOOD
    )

    assert (
        reading.source
        == ReadingSource.HARDWARE
    )

    assert reading.unit == "C"

    assert downstream == [
        "alert"
    ]


# ============================================================
# AUTOMATION WIRING
# ============================================================


async def test_configured_executor_runs_automation_after_commit(
    test_session,
    monkeypatch,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    reader = RecordingReader()

    call_order = []

    executor = object()

    async def fake_alert(
        session,
        reading,
    ):
        assert (
            await session.get(
                SensorReading,
                reading.id,
            )
            is not None
        )

        call_order.append(
            "alert"
        )

        return None

    async def fake_automation(
        session,
        *,
        reading,
        executor,
        current_time=None,
    ):
        assert (
            await session.get(
                SensorReading,
                reading.id,
            )
            is not None
        )

        assert executor is not None

        call_order.append(
            "automation"
        )

        return None

    monkeypatch.setattr(
        acquisition_service,
        "process_sensor_reading",
        fake_alert,
    )

    monkeypatch.setattr(
        acquisition_service,
        "process_sensor_reading_automation",
        fake_automation,
    )

    await acquire_hardware_sensor_reading(
        test_session,
        sensor_id=sensor.id,
        reader=reader,
        actuator_executor=executor,
    )

    assert call_order == [
        "alert",
        "automation",
    ]


# ============================================================
# SIMULATED SENSOR PROTECTION
# ============================================================


async def test_simulated_sensor_cannot_use_hardware_acquisition(
    test_session,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
        is_simulated=True,
    )

    reader = RecordingReader()

    with pytest.raises(
        HardwareSensorAcquisitionError,
        match=(
            "Simulated sensor cannot use "
            "hardware acquisition"
        ),
    ):
        await acquire_hardware_sensor_reading(
            test_session,
            sensor_id=sensor.id,
            reader=reader,
        )

    assert reader.identifiers == []

    assert (
        await get_sensor_readings(
            test_session,
            sensor,
        )
        == []
    )


# ============================================================
# HARDWARE IDENTIFIER
# ============================================================


async def test_missing_hardware_identifier_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
        hardware_identifier=None,
    )

    reader = RecordingReader()

    with pytest.raises(
        HardwareSensorAcquisitionError,
        match=(
            "Hardware sensor has no "
            "hardware identifier"
        ),
    ):
        await acquire_hardware_sensor_reading(
            test_session,
            sensor_id=sensor.id,
            reader=reader,
        )

    assert reader.identifiers == []


async def test_reader_identifier_mismatch_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    reader = RecordingReader(
        result=HardwareSensorReading(
            hardware_identifier=(
                "28-111111111111"
            ),
            value_numeric=23.5,
            recorded_at=RECORDED_AT,
        )
    )

    with pytest.raises(
        HardwareSensorAcquisitionError,
        match=(
            "does not match the "
            "configured sensor"
        ),
    ):
        await acquire_hardware_sensor_reading(
            test_session,
            sensor_id=sensor.id,
            reader=reader,
        )

    assert (
        await get_sensor_readings(
            test_session,
            sensor,
        )
        == []
    )


# ============================================================
# TIMESTAMP VALIDATION
# ============================================================


async def test_naive_hardware_timestamp_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    reader = RecordingReader(
        result=HardwareSensorReading(
            hardware_identifier=(
                DEVICE_ID
            ),
            value_numeric=23.5,
            recorded_at=datetime(
                2026,
                9,
                4,
                7,
                0,
                0,
            ),
        )
    )

    with pytest.raises(
        HardwareSensorAcquisitionError,
        match=(
            "timezone-aware timestamp"
        ),
    ):
        await acquire_hardware_sensor_reading(
            test_session,
            sensor_id=sensor.id,
            reader=reader,
        )

    assert (
        await get_sensor_readings(
            test_session,
            sensor,
        )
        == []
    )


# ============================================================
# NON-FINITE NUMERIC PROTECTION
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
async def test_non_finite_hardware_value_is_rejected(
    test_session,
    value,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    reader = RecordingReader(
        result=HardwareSensorReading(
            hardware_identifier=(
                DEVICE_ID
            ),
            value_numeric=value,
            recorded_at=RECORDED_AT,
        )
    )

    with pytest.raises(
        HardwareSensorAcquisitionError,
        match=(
            "non-finite value"
        ),
    ):
        await acquire_hardware_sensor_reading(
            test_session,
            sensor_id=sensor.id,
            reader=reader,
        )

    assert (
        await get_sensor_readings(
            test_session,
            sensor,
        )
        == []
    )