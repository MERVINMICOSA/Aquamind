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
from app.models.automation import AutomationRule
from app.models.system import AquaponicsSystem
from app.services.actuator_executor import (
    ActuatorExecutionResult,
)
from app.services.automation_runtime_service import (
    create_automation_execution_records,
    execute_and_reconcile_automation_execution,
    prepare_automation_execution_request,
)
from app.services.automation_service import (
    prepare_sensor_threshold_automation_decision,
)


pytestmark = pytest.mark.asyncio


async def prepare_execution(
    session,
    *,
    current_value=None,
):
    system = AquaponicsSystem(
        name="State Reconciliation System",
    )

    session.add(system)
    await session.commit()
    await session.refresh(system)

    rule = AutomationRule(
        system_id=system.id,
        name="State Reconciliation Rule",
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

    actuator = Actuator(
        system_id=system.id,
        name="State Water Pump",
        actuator_type=(
            ActuatorType.WATER_PUMP
        ),
        control_mode=(
            ControlMode.AUTOMATIC
        ),
        hardware_identifier="STATE-PUMP-001",
        location_type=None,
        location_id=None,
        is_enabled=True,
        safety_config=None,
        current_state=ActuatorState.OFF,
        current_value=current_value,
        last_state_at=None,
        deleted_at=None,
    )

    session.add(actuator)
    await session.commit()
    await session.refresh(actuator)

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


class CompletedExecutor:
    def __init__(
        self,
        *,
        completed_at,
        actual_value,
    ):
        self.completed_at = completed_at
        self.actual_value = actual_value

    async def execute(
        self,
        command,
    ):
        return ActuatorExecutionResult(
            status=ExecutionStatus.COMPLETED,
            completed_at=self.completed_at,
            actual_value=self.actual_value,
            result_summary="Actuator activated",
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
            actual_value=0.2,
            result_summary="Activation failed",
            fault_code="ACTUATOR_FAULT",
            error_message="Actuator did not activate",
        )


class RaisingExecutor:
    async def execute(
        self,
        command,
    ):
        raise RuntimeError(
            "Hardware unavailable"
        )


async def test_completed_activation_updates_actuator_state(
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
        + timedelta(seconds=1)
    )

    await execute_and_reconcile_automation_execution(
        test_session,
        request=request,
        records=records,
        executor=CompletedExecutor(
            completed_at=completed_at,
            actual_value=0.95,
        ),
    )

    await test_session.refresh(
        actuator
    )

    assert (
        actuator.current_state
        == ActuatorState.ON
    )

    assert (
        float(actuator.current_value)
        == pytest.approx(0.95)
    )

    assert actuator.last_state_at is not None

    # SQLite may return TIMESTAMPTZ without tzinfo.
    persisted_last_state = (
        actuator.last_state_at
    )

    if persisted_last_state.tzinfo is None:
        persisted_last_state = (
            persisted_last_state.replace(
                tzinfo=timezone.utc
            )
        )

    assert (
        persisted_last_state
        == completed_at
    )


async def test_completed_activation_without_actual_value_preserves_current_value(
    test_session,
):
    (
        actuator,
        request,
        records,
        started_at,
    ) = await prepare_execution(
        test_session,
        current_value=0.4,
    )

    await execute_and_reconcile_automation_execution(
        test_session,
        request=request,
        records=records,
        executor=CompletedExecutor(
            completed_at=(
                started_at
                + timedelta(seconds=1)
            ),
            actual_value=None,
        ),
    )

    await test_session.refresh(
        actuator
    )

    assert (
        actuator.current_state
        == ActuatorState.ON
    )

    assert (
        float(actuator.current_value)
        == pytest.approx(0.4)
    )

    assert actuator.last_state_at is not None


async def test_failed_execution_does_not_change_actuator_state(
    test_session,
):
    (
        actuator,
        request,
        records,
        started_at,
    ) = await prepare_execution(
        test_session,
        current_value=0.0,
    )

    await execute_and_reconcile_automation_execution(
        test_session,
        request=request,
        records=records,
        executor=FailedExecutor(
            completed_at=(
                started_at
                + timedelta(seconds=2)
            ),
        ),
    )

    await test_session.refresh(
        actuator
    )

    assert (
        actuator.current_state
        == ActuatorState.OFF
    )

    assert (
        float(actuator.current_value)
        == pytest.approx(0.0)
    )

    assert actuator.last_state_at is None


async def test_executor_exception_does_not_change_actuator_state(
    test_session,
):
    (
        actuator,
        request,
        records,
        _,
    ) = await prepare_execution(
        test_session,
        current_value=0.0,
    )

    from app.services.automation_runtime_service import (
        AutomationRuntimeServiceError,
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match="Actuator execution failed",
    ):
        await execute_and_reconcile_automation_execution(
            test_session,
            request=request,
            records=records,
            executor=RaisingExecutor(),
        )

    await test_session.refresh(
        actuator
    )

    assert (
        actuator.current_state
        == ActuatorState.OFF
    )

    assert (
        float(actuator.current_value)
        == pytest.approx(0.0)
    )

    assert actuator.last_state_at is None