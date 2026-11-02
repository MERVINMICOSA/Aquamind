from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from app.db.enums import (
    ActuatorState,
    ActuatorType,
    AutomationTriggerType,
    ControlMode,
    ExecutionStatus,
)
from app.models.actuators import Actuator
from app.models.automation import (
    AutomationRule,
)
from app.models.system import AquaponicsSystem
from app.services.actuator_executor import (
    ActuatorExecutionResult,
)
from app.services.automation_runtime_service import (
    AutomationRuntimeServiceError,
    create_automation_execution_records,
    execute_automation_execution_records,
    prepare_automation_execution_request,
)
from app.services.automation_service import (
    prepare_sensor_threshold_automation_decision,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# HELPERS
# ============================================================


async def create_system(
    session,
):
    system = AquaponicsSystem(
        name="Executor Runtime System",
    )

    session.add(system)

    await session.commit()
    await session.refresh(system)

    return system


async def create_rule(
    session,
    system,
):
    rule = AutomationRule(
        system_id=system.id,
        name="Executor Low pH Rule",
        description=None,
        trigger_type=(
            AutomationTriggerType.SENSOR_THRESHOLD
        ),
        condition_definition={
            "sensor_type": "ph",
            "measurement_type": "ph",
            "operator": "less_than",
            "value": 6.0,
        },
        action_definition={
            "action": "activate_actuator",
            "actuator_type": "water_pump",
            "value": 1.0,
        },
        enabled=True,
        priority=20,
        cooldown_seconds=300,
    )

    session.add(rule)

    await session.commit()
    await session.refresh(rule)

    return rule


async def create_actuator(
    session,
    system,
):
    actuator = Actuator(
        system_id=system.id,
        name="Executor Water Pump",
        actuator_type=(
            ActuatorType.WATER_PUMP
        ),
        control_mode=(
            ControlMode.AUTOMATIC
        ),
        hardware_identifier=(
            "AUTO-PUMP-001"
        ),
        location_type=None,
        location_id=None,
        is_enabled=True,
        safety_config=None,
        current_state=ActuatorState.OFF,
        current_value=None,
        last_state_at=None,
        deleted_at=None,
    )

    session.add(actuator)

    await session.commit()
    await session.refresh(actuator)

    return actuator


async def prepare_execution(
    session,
):
    system = await create_system(
        session
    )

    rule = await create_rule(
        session,
        system,
    )

    actuator = await create_actuator(
        session,
        system,
    )

    started_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    decision = (
        await prepare_sensor_threshold_automation_decision(
            session,
            rule_id=rule.id,
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=5.8,
            current_time=started_at,
        )
    )

    request = (
        await prepare_automation_execution_request(
            session,
            decision=decision,
        )
    )

    records = (
        await create_automation_execution_records(
            session,
            request=request,
            started_at=started_at,
        )
    )

    return (
        actuator,
        request,
        records,
        started_at,
    )


# ============================================================
# TEST EXECUTORS
# ============================================================


class SuccessfulExecutor:
    def __init__(
        self,
        *,
        session,
        records,
        completed_at,
    ):
        self.session = session
        self.records = records
        self.completed_at = completed_at
        self.command = None

    async def execute(
        self,
        command,
    ):
        self.command = command

        await self.session.refresh(
            self.records.automation_run
        )

        await self.session.refresh(
            self.records.actuator_event
        )

        # RUNNING must be persisted before dispatch.
        assert (
            self.records.automation_run.status
            == ExecutionStatus.RUNNING
        )

        assert (
            self.records.actuator_event.status
            == ExecutionStatus.RUNNING
        )

        return ActuatorExecutionResult(
            status=ExecutionStatus.COMPLETED,
            completed_at=self.completed_at,
            actual_value=1.0,
            result_summary=(
                "Water pump activated"
            ),
        )


class FailedExecutor:
    def __init__(
        self,
        *,
        completed_at,
    ):
        self.completed_at = completed_at

    async def execute(
        self,
        command,
    ):
        return ActuatorExecutionResult(
            status=ExecutionStatus.FAILED,
            completed_at=self.completed_at,
            actual_value=0.25,
            result_summary=(
                "Water pump activation failed"
            ),
            fault_code="PUMP_FAULT",
            error_message=(
                "Pump did not reach requested output"
            ),
        )


class RaisingExecutor:
    async def execute(
        self,
        command,
    ):
        raise RuntimeError(
            "Hardware transport unavailable"
        )


class InvalidExecutor:
    def __init__(
        self,
        *,
        completed_at,
    ):
        self.completed_at = completed_at

    async def execute(
        self,
        command,
    ):
        return ActuatorExecutionResult(
            status=ExecutionStatus.RUNNING,
            completed_at=self.completed_at,
            actual_value=None,
        )


# ============================================================
# SUCCESS
# ============================================================


async def test_successful_executor_completes_both_records(
    test_session,
):
    (
        actuator,
        request,
        records,
        started_at,
    ) = await prepare_execution(
        test_session
    )

    completed_at = (
        started_at
        + timedelta(milliseconds=1250)
    )

    executor = SuccessfulExecutor(
        session=test_session,
        records=records,
        completed_at=completed_at,
    )

    result = (
        await execute_automation_execution_records(
            test_session,
            request=request,
            records=records,
            executor=executor,
        )
    )

    run = result.automation_run
    event = result.actuator_event

    assert (
        run.status
        == ExecutionStatus.COMPLETED
    )

    assert run.completed_at is not None

    assert (
        run.result_summary
        == "Water pump activated"
    )

    assert run.error_message is None

    assert (
        event.status
        == ExecutionStatus.COMPLETED
    )

    assert (
        float(event.actual_value)
        == pytest.approx(1.0)
    )

    assert event.duration_ms == 1250

    assert event.fault_code is None
    assert event.error_message is None

    assert executor.command is not None

    assert (
        executor.command.actuator_id
        == actuator.id
    )

    assert (
        executor.command.hardware_identifier
        == "AUTO-PUMP-001"
    )

    assert (
        executor.command.requested_value
        == pytest.approx(1.0)
    )


# ============================================================
# FAILURE RESULT
# ============================================================


async def test_failed_executor_result_fails_both_records(
    test_session,
):
    (
        _,
        request,
        records,
        started_at,
    ) = await prepare_execution(
        test_session
    )

    executor = FailedExecutor(
        completed_at=(
            started_at
            + timedelta(seconds=2)
        )
    )

    result = (
        await execute_automation_execution_records(
            test_session,
            request=request,
            records=records,
            executor=executor,
        )
    )

    run = result.automation_run
    event = result.actuator_event

    assert (
        run.status
        == ExecutionStatus.FAILED
    )

    assert (
        run.error_message
        == "Pump did not reach requested output"
    )

    assert (
        event.status
        == ExecutionStatus.FAILED
    )

    assert event.duration_ms == 2000

    assert (
        event.fault_code
        == "PUMP_FAULT"
    )

    assert (
        event.error_message
        == "Pump did not reach requested output"
    )


# ============================================================
# EXECUTOR EXCEPTION
# ============================================================


async def test_executor_exception_is_persisted_as_failure(
    test_session,
):
    (
        _,
        request,
        records,
        _,
    ) = await prepare_execution(
        test_session
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match="Actuator execution failed",
    ):
        await execute_automation_execution_records(
            test_session,
            request=request,
            records=records,
            executor=RaisingExecutor(),
        )

    await test_session.refresh(
        records.automation_run
    )

    await test_session.refresh(
        records.actuator_event
    )

    assert (
        records.automation_run.status
        == ExecutionStatus.FAILED
    )

    assert (
        records.actuator_event.status
        == ExecutionStatus.FAILED
    )

    assert (
        "Hardware transport unavailable"
        in records.automation_run.error_message
    )

    assert (
        "Hardware transport unavailable"
        in records.actuator_event.error_message
    )


# ============================================================
# INVALID EXECUTOR RESULT
# ============================================================


async def test_nonterminal_executor_result_does_not_leave_running_records(
    test_session,
):
    (
        _,
        request,
        records,
        started_at,
    ) = await prepare_execution(
        test_session
    )

    executor = InvalidExecutor(
        completed_at=(
            started_at
            + timedelta(seconds=1)
        )
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Actuator executor must return "
            "a terminal status"
        ),
    ):
        await execute_automation_execution_records(
            test_session,
            request=request,
            records=records,
            executor=executor,
        )

    await test_session.refresh(
        records.automation_run
    )

    await test_session.refresh(
        records.actuator_event
    )

    assert (
        records.automation_run.status
        == ExecutionStatus.FAILED
    )

    assert (
        records.actuator_event.status
        == ExecutionStatus.FAILED
    )


# ============================================================
# ACTUATOR STATE BOUNDARY
# ============================================================


async def test_executor_lifecycle_does_not_reconcile_actuator_state(
    test_session,
):
    (
        actuator,
        request,
        records,
        started_at,
    ) = await prepare_execution(
        test_session
    )

    executor = SuccessfulExecutor(
        session=test_session,
        records=records,
        completed_at=(
            started_at
            + timedelta(seconds=1)
        ),
    )

    await execute_automation_execution_records(
        test_session,
        request=request,
        records=records,
        executor=executor,
    )

    await test_session.refresh(
        actuator
    )

    assert (
        actuator.current_state
        == ActuatorState.OFF
    )

    assert actuator.current_value is None
    assert actuator.last_state_at is None