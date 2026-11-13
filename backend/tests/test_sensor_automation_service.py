from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest
from sqlalchemy import select

from app.db.enums import (
    ActuatorState,
    ActuatorType,
    AutomationTriggerType,
    CalibrationStatus,
    ControlMode,
    ExecutionStatus,
    LocationType,
    MeasurementType,
    ReadingQuality,
    ReadingSource,
    SensorType,
)
from app.models.actuators import (
    Actuator,
    ActuatorEvent,
)
from app.models.automation import (
    AutomationRule,
    AutomationRun,
)
from app.models.sensors import (
    Sensor,
    SensorReading,
)
from app.models.system import (
    AquaponicsSystem,
)
from app.services.actuator_executor import (
    ActuatorExecutionResult,
)
from app.services.sensor_automation_service import (
    SensorAutomationOutcome,
    process_sensor_reading_automation,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# FIXED TIME
# ============================================================


PROCESSING_TIME = datetime(
    2026,
    1,
    1,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


# ============================================================
# TEST EXECUTOR
# ============================================================


class RecordingExecutor:
    def __init__(self):
        self.commands = []

    async def execute(
        self,
        command,
    ):
        self.commands.append(
            command
        )

        return ActuatorExecutionResult(
            status=ExecutionStatus.COMPLETED,
            completed_at=(
                PROCESSING_TIME
                + timedelta(seconds=1)
            ),
            actual_value=(
                command.requested_value
            ),
            result_summary=(
                "Automation command completed"
            ),
        )


# ============================================================
# HELPERS
# ============================================================


async def create_system(
    session,
    *,
    name="Sensor Automation System",
):
    system = AquaponicsSystem(
        name=name,
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
        name="Automation pH Sensor",
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
        calibration_status=CalibrationStatus.VERIFIED,
    )

    session.add(sensor)

    await session.commit()
    await session.refresh(sensor)

    return sensor


async def create_reading(
    session,
    sensor,
    *,
    value=5.5,
    quality=ReadingQuality.GOOD,
):
    reading = SensorReading(
        sensor_id=sensor.id,
        recorded_at=PROCESSING_TIME,
        value_numeric=value,
        unit="pH",
        quality_status=quality,
        source=next(
            iter(ReadingSource)
        ),
        sequence_number=None,
    )

    session.add(reading)

    await session.commit()
    await session.refresh(reading)

    return reading


async def create_actuator(
    session,
    system,
    *,
    name,
    actuator_type,
):
    actuator = Actuator(
        system_id=system.id,
        name=name,
        actuator_type=actuator_type,
        control_mode=ControlMode.AUTOMATIC,
        hardware_identifier=None,
        location_type=None,
        location_id=None,
        is_enabled=True,
        safety_config=None,
        current_state=ActuatorState.OFF,
        current_value=0,
        last_state_at=None,
        deleted_at=None,
    )

    session.add(actuator)

    await session.commit()
    await session.refresh(actuator)

    return actuator


async def create_rule(
    session,
    system,
    *,
    name,
    priority,
    actuator_type="water_pump",
    threshold=6.0,
    enabled=True,
):
    rule = AutomationRule(
        system_id=system.id,
        name=name,
        description=None,
        trigger_type=(
            AutomationTriggerType.SENSOR_THRESHOLD
        ),
        condition_definition={
            "sensor_type": "ph",
            "measurement_type": "ph",
            "operator": "less_than",
            "value": threshold,
        },
        action_definition={
            "action": "activate_actuator",
            "actuator_type": actuator_type,
            "value": 1.0,
        },
        enabled=enabled,
        priority=priority,
        cooldown_seconds=0,
    )

    session.add(rule)

    await session.commit()
    await session.refresh(rule)

    return rule


# ============================================================
# PRIORITY + SAME-ACTUATOR ARBITRATION
# ============================================================


async def test_higher_priority_rule_wins_same_actuator(
    test_session,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    reading = await create_reading(
        test_session,
        sensor,
    )

    actuator = await create_actuator(
        test_session,
        system,
        name="Main Water Pump",
        actuator_type=(
            ActuatorType.WATER_PUMP
        ),
    )

    high = await create_rule(
        test_session,
        system,
        name="High Priority Rule",
        priority=100,
    )

    low = await create_rule(
        test_session,
        system,
        name="Low Priority Rule",
        priority=10,
    )

    executor = RecordingExecutor()

    result = (
        await process_sensor_reading_automation(
            test_session,
            reading=reading,
            executor=executor,
            current_time=PROCESSING_TIME,
        )
    )

    assert len(
        executor.commands
    ) == 1

    assert (
        executor.commands[0].actuator_id
        == actuator.id
    )

    assert len(
        result.rule_results
    ) == 2

    assert (
        result.rule_results[0].rule_id
        == high.id
    )

    assert (
        result.rule_results[0].outcome
        == SensorAutomationOutcome.EXECUTED
    )

    assert (
        result.rule_results[1].rule_id
        == low.id
    )

    assert (
        result.rule_results[1].outcome
        == SensorAutomationOutcome.SUPERSEDED
    )

    run_result = await test_session.execute(
        select(AutomationRun)
    )

    runs = list(
        run_result.scalars().all()
    )

    assert len(runs) == 1
    assert runs[0].rule_id == high.id

    event_result = await test_session.execute(
        select(ActuatorEvent)
    )

    events = list(
        event_result.scalars().all()
    )

    assert len(events) == 1


# ============================================================
# DIFFERENT ACTUATORS MAY BOTH EXECUTE
# ============================================================


async def test_matching_rules_for_different_actuators_both_execute(
    test_session,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    reading = await create_reading(
        test_session,
        sensor,
    )

    await create_actuator(
        test_session,
        system,
        name="Water Pump",
        actuator_type=(
            ActuatorType.WATER_PUMP
        ),
    )

    await create_actuator(
        test_session,
        system,
        name="Oxygen Pump",
        actuator_type=(
            ActuatorType.OXYGEN_PUMP
        ),
    )

    high = await create_rule(
        test_session,
        system,
        name="Water Rule",
        priority=20,
        actuator_type="water_pump",
    )

    low = await create_rule(
        test_session,
        system,
        name="Oxygen Rule",
        priority=10,
        actuator_type="oxygen_pump",
    )

    executor = RecordingExecutor()

    result = (
        await process_sensor_reading_automation(
            test_session,
            reading=reading,
            executor=executor,
            current_time=PROCESSING_TIME,
        )
    )

    assert len(
        executor.commands
    ) == 2

    # Existing convention: descending priority.
    assert (
        executor.commands[0].actuator_type
        == ActuatorType.WATER_PUMP
    )

    assert (
        executor.commands[1].actuator_type
        == ActuatorType.OXYGEN_PUMP
    )

    assert (
        result.executed_count
        == 2
    )

    assert (
        result.rule_results[0].rule_id
        == high.id
    )

    assert (
        result.rule_results[1].rule_id
        == low.id
    )


# ============================================================
# NON-MATCHING CONDITION
# ============================================================


async def test_nonmatching_rule_does_not_create_execution_records(
    test_session,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    reading = await create_reading(
        test_session,
        sensor,
        value=7.0,
    )

    await create_actuator(
        test_session,
        system,
        name="Water Pump",
        actuator_type=(
            ActuatorType.WATER_PUMP
        ),
    )

    await create_rule(
        test_session,
        system,
        name="Low pH Rule",
        priority=10,
        threshold=6.0,
    )

    executor = RecordingExecutor()

    result = (
        await process_sensor_reading_automation(
            test_session,
            reading=reading,
            executor=executor,
            current_time=PROCESSING_TIME,
        )
    )

    assert executor.commands == []

    assert len(
        result.rule_results
    ) == 1

    assert (
        result.rule_results[0].outcome
        == SensorAutomationOutcome.SKIPPED
    )

    assert (
        result.rule_results[0].reason
        == "condition_not_matched"
    )

    run_result = await test_session.execute(
        select(AutomationRun)
    )

    assert (
        run_result.scalars().all()
        == []
    )


# ============================================================
# RULE FAILURE ISOLATION
# ============================================================


async def test_invalid_rule_does_not_block_lower_priority_valid_rule(
    test_session,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    reading = await create_reading(
        test_session,
        sensor,
    )

    await create_actuator(
        test_session,
        system,
        name="Water Pump",
        actuator_type=(
            ActuatorType.WATER_PUMP
        ),
    )

    invalid_rule = await create_rule(
        test_session,
        system,
        name="Invalid High Priority Rule",
        priority=100,
        actuator_type="unsupported_actuator",
    )

    valid_rule = await create_rule(
        test_session,
        system,
        name="Valid Lower Priority Rule",
        priority=10,
        actuator_type="water_pump",
    )

    executor = RecordingExecutor()

    result = (
        await process_sensor_reading_automation(
            test_session,
            reading=reading,
            executor=executor,
            current_time=PROCESSING_TIME,
        )
    )

    assert len(
        executor.commands
    ) == 1

    by_rule = {
        item.rule_id: item
        for item in result.rule_results
    }

    assert (
        by_rule[
            invalid_rule.id
        ].outcome
        == SensorAutomationOutcome.FAILED
    )

    assert (
        "Unsupported automation actuator type"
        in by_rule[
            invalid_rule.id
        ].reason
    )

    assert (
        by_rule[
            valid_rule.id
        ].outcome
        == SensorAutomationOutcome.EXECUTED
    )


# ============================================================
# READING QUALITY
# ============================================================


async def test_non_good_reading_never_triggers_automation(
    test_session,
):
    system = await create_system(
        test_session
    )

    sensor = await create_sensor(
        test_session,
        system,
    )

    non_good_quality = next(
        quality
        for quality in ReadingQuality
        if quality != ReadingQuality.GOOD
    )

    reading = await create_reading(
        test_session,
        sensor,
        quality=non_good_quality,
    )

    await create_actuator(
        test_session,
        system,
        name="Water Pump",
        actuator_type=(
            ActuatorType.WATER_PUMP
        ),
    )

    await create_rule(
        test_session,
        system,
        name="Low pH Rule",
        priority=10,
    )

    executor = RecordingExecutor()

    result = (
        await process_sensor_reading_automation(
            test_session,
            reading=reading,
            executor=executor,
            current_time=PROCESSING_TIME,
        )
    )

    assert executor.commands == []
    assert result.rule_results == ()

    run_result = await test_session.execute(
        select(AutomationRun)
    )

    assert (
        run_result.scalars().all()
        == []
    )

    event_result = await test_session.execute(
        select(ActuatorEvent)
    )

    assert (
        event_result.scalars().all()
        == []
    )

# ============================================================
# CALIBRATION-DEPENDENT AUTOMATION SAFETY
# ============================================================


@pytest.mark.parametrize(
    "calibration_status",
    [
        CalibrationStatus.PENDING,
        CalibrationStatus.REJECTED,
        CalibrationStatus.EXPIRED,
    ],
)
async def test_unverified_ph_cannot_command_an_actuator(
    test_session,
    calibration_status,
):
    system = await create_system(test_session)
    sensor = await create_sensor(test_session, system)
    sensor.calibration_status = calibration_status
    await test_session.commit()

    reading = await create_reading(test_session, sensor)
    await create_actuator(
        test_session,
        system,
        name="Safety test pump",
        actuator_type=ActuatorType.WATER_PUMP,
    )
    await create_rule(
        test_session,
        system,
        name="Would activate if trusted",
        priority=10,
    )

    executor = RecordingExecutor()
    result = await process_sensor_reading_automation(
        test_session,
        reading=reading,
        executor=executor,
        current_time=PROCESSING_TIME,
    )

    assert executor.commands == []
    assert result.rule_results == ()
    runs = await test_session.execute(select(AutomationRun))
    assert runs.scalars().all() == []
