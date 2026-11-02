from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.api import sensor_readings as sensor_readings_api
from app.db.enums import (
    LocationType,
    MeasurementType,
    ReadingQuality,
    ReadingSource,
    SensorType,
)
from app.models.sensors import (
    Sensor,
    SensorReading,
)
from app.models.system import (
    AquaponicsSystem,
)
from app.schemas.sensor_reading import (
    SensorReadingCreate,
)


pytestmark = pytest.mark.asyncio


RECORDED_AT = datetime(
    2026,
    1,
    1,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


# ============================================================
# HELPERS
# ============================================================


async def create_system(
    session,
):
    system = AquaponicsSystem(
        name="Sensor Wiring System",
    )

    session.add(system)

    await session.commit()
    await session.refresh(system)

    return system


async def create_sensor(
    session,
    system,
):
    sensor = Sensor(
        system_id=system.id,
        name="Wiring pH Sensor",
        sensor_type=SensorType("ph"),
        measurement_type=(
            MeasurementType("ph")
        ),
        location_type=next(
            iter(LocationType)
        ),
        location_id=None,
        unit="pH",
        hardware_identifier=None,
        is_simulated=True,
        is_enabled=True,
        sampling_interval_seconds=30,
    )

    session.add(sensor)

    await session.commit()
    await session.refresh(sensor)

    return sensor


def create_payload(
    sensor,
):
    return SensorReadingCreate(
        sensor_id=sensor.id,
        recorded_at=RECORDED_AT,
        value_numeric=5.8,
        unit="pH",
        quality_status=(
            ReadingQuality.GOOD
        ),
        source=next(
            iter(ReadingSource)
        ),
        sequence_number=1,
    )


# ============================================================
# NO EXECUTOR
# ============================================================


async def test_sensor_reading_succeeds_without_actuator_executor(
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

    payload = create_payload(
        sensor
    )

    alert_calls = []

    async def fake_alert_processing(
        session,
        reading,
    ):
        # Reading must already exist in persistence before
        # downstream processing starts.
        persisted = await session.get(
            SensorReading,
            reading.id,
        )

        assert persisted is not None

        alert_calls.append(
            reading.id
        )

        return None

    async def automation_must_not_run(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Automation must not run without "
            "a configured actuator executor"
        )

    monkeypatch.setattr(
        sensor_readings_api,
        "process_sensor_reading",
        fake_alert_processing,
    )

    monkeypatch.setattr(
        sensor_readings_api,
        "process_sensor_reading_automation",
        automation_must_not_run,
    )

    reading = (
        await sensor_readings_api.create_sensor_reading(
            payload=payload,
            session=test_session,
            actuator_executor=None,
        )
    )

    assert reading.id is not None

    persisted = await test_session.get(
        SensorReading,
        reading.id,
    )

    assert persisted is not None

    assert alert_calls == [
        reading.id
    ]


# ============================================================
# CONFIGURED EXECUTOR
# ============================================================


async def test_configured_executor_invokes_automation_after_persistence(
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

    payload = create_payload(
        sensor
    )

    call_order = []

    class DummyExecutor:
        async def execute(
            self,
            command,
        ):
            raise AssertionError(
                "The wiring test must not directly "
                "execute hardware"
            )

    executor = DummyExecutor()

    async def fake_alert_processing(
        session,
        reading,
    ):
        persisted = await session.get(
            SensorReading,
            reading.id,
        )

        assert persisted is not None

        call_order.append(
            "alert"
        )

        return None

    async def fake_automation_processing(
        session,
        *,
        reading,
        executor: object,
        current_time=None,
    ):
        persisted = await session.get(
            SensorReading,
            reading.id,
        )

        assert persisted is not None

        assert executor is not None

        call_order.append(
            "automation"
        )

        return None

    monkeypatch.setattr(
        sensor_readings_api,
        "process_sensor_reading",
        fake_alert_processing,
    )

    monkeypatch.setattr(
        sensor_readings_api,
        "process_sensor_reading_automation",
        fake_automation_processing,
    )

    reading = (
        await sensor_readings_api.create_sensor_reading(
            payload=payload,
            session=test_session,
            actuator_executor=executor,
        )
    )

    assert reading.id is not None

    assert call_order == [
        "alert",
        "automation",
    ]