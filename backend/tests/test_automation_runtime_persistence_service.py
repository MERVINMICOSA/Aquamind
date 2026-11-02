from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from sqlalchemy import select

import pytest

from app.db.enums import (
    ActuatorCommandType,
    ActuatorState,
    ActuatorType,
    AutomationTriggerType,
    ControlMode,
    ExecutionStatus,
    TriggerSource,
)

from app.models.actuators import (
    Actuator,
    ActuatorEvent,
)

from app.models.actuators import Actuator
from app.models.automation import AutomationRule
from app.models.system import AquaponicsSystem
from app.services.automation_runtime_service import (
    AutomationRuntimeServiceError,
    create_automation_execution_records,
    prepare_automation_execution_request,
)
from app.services.automation_service import (
    prepare_sensor_threshold_automation_decision,
)
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from app.models.automation import (
    AutomationRule,
    AutomationRun,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# HELPERS
# ============================================================


async def create_system(
    session,
    *,
    name="Runtime Persistence System",
):
    system = AquaponicsSystem(
        name=name,
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
        name="Low pH Runtime Rule",
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
        name="Runtime Water Pump",
        actuator_type=(
            ActuatorType.WATER_PUMP
        ),
        control_mode=(
            ControlMode.AUTOMATIC
        ),
        hardware_identifier=None,
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


async def prepare_request(
    session,
    rule,
):
    decision = (
        await prepare_sensor_threshold_automation_decision(
            session,
            rule_id=rule.id,
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=5.8,
            current_time=datetime(
                2026,
                1,
                1,
                12,
                0,
                0,
                tzinfo=timezone.utc,
            ),
        )
    )

    return (
        await prepare_automation_execution_request(
            session,
            decision=decision,
        )
    )


# ============================================================
# RECORD CREATION
# ============================================================


async def test_creates_pending_run_and_actuator_event(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    actuator = await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
    )

    started_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        1,
        tzinfo=timezone.utc,
    )

    records = (
        await create_automation_execution_records(
            test_session,
            request=request,
            started_at=started_at,
        )
    )

    run = records.automation_run
    event = records.actuator_event

    assert run.id is not None
    assert run.rule_id == rule.id

    assert (
        run.status
        == ExecutionStatus.PENDING
    )

    assert run.completed_at is None

    assert (
        run.trigger_value
        == pytest.approx(5.8)
    )

    assert run.result_summary is None
    assert run.error_message is None

    assert event.id is not None

    assert (
        event.actuator_id
        == actuator.id
    )

    assert (
        event.command_type
        == ActuatorCommandType.ACTIVATE
    )

    assert (
        float(event.requested_value)
        == pytest.approx(1.0)
    )

    assert event.actual_value is None

    assert (
        event.trigger_source
        == TriggerSource.AUTOMATION
    )

    assert (
        event.status
        == ExecutionStatus.PENDING
    )

    assert event.completed_at is None
    assert event.duration_ms is None
    assert event.fault_code is None
    assert event.error_message is None


# ============================================================
# NO HARDWARE SIDE EFFECT YET
# ============================================================


async def test_preparing_records_does_not_change_actuator_state(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    actuator = await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
    )

    await create_automation_execution_records(
        test_session,
        request=request,
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


# ============================================================
# STALE TARGET PROTECTION
# ============================================================


async def test_actuator_is_revalidated_before_records_are_created(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    actuator = await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
    )

    actuator.is_enabled = False

    await test_session.commit()

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation actuator is no longer eligible"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=request,
        )


# ============================================================
# REQUEST CONSISTENCY
# ============================================================


async def test_request_system_must_match_rule(
    test_session,
):
    system = await create_system(
        test_session,
        name="Rule System",
    )

    other_system = await create_system(
        test_session,
        name="Other System",
    )

    rule = await create_rule(
        test_session,
        system,
    )

    await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
    )

    invalid_request = replace(
        request,
        system_id=other_system.id,
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation execution request system "
            "does not match rule"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=invalid_request,
        )


async def test_non_automation_trigger_source_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
    )

    invalid_request = replace(
        request,
        trigger_source=TriggerSource.MANUAL,
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation execution request must use "
            "automation trigger source"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=invalid_request,
        )


# ============================================================
# TIME VALIDATION
# ============================================================


async def test_naive_execution_start_time_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation execution start time is invalid"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=request,
            started_at=datetime(
                2026,
                1,
                1,
                12,
                0,
                0,
            ),
        )


# ============================================================
# STALE DECISION / EXECUTION CLAIM
# ============================================================


async def test_stale_request_is_blocked_when_run_became_active(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    await create_actuator(
        test_session,
        system,
    )

    # Both requests are prepared while the rule is eligible.
    first_request = await prepare_request(
        test_session,
        rule,
    )

    second_request = await prepare_request(
        test_session,
        rule,
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

    first_records = (
        await create_automation_execution_records(
            test_session,
            request=first_request,
            started_at=started_at,
        )
    )

    assert (
        first_records.automation_run.status
        == ExecutionStatus.PENDING
    )

    # second_request was valid when prepared, but must not
    # create another run after the first request claimed it.
    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation rule is no longer eligible: "
            "run_active"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=second_request,
            started_at=(
                started_at
                + timedelta(milliseconds=100)
            ),
        )

    result = await test_session.execute(
        select(AutomationRun).where(
            AutomationRun.rule_id
            == rule.id
        )
    )

    runs = list(
        result.scalars().all()
    )

    assert len(runs) == 1


async def test_stale_request_is_blocked_when_rule_was_disabled(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
    )

    # Configuration changed after the original decision.
    rule.enabled = False

    await test_session.commit()

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation rule is no longer eligible: "
            "disabled"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=request,
            started_at=datetime(
                2026,
                1,
                1,
                12,
                0,
                0,
                tzinfo=timezone.utc,
            ),
        )


async def test_stale_request_is_blocked_when_cooldown_became_active(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
    )

    current_time = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    # Another execution completes after the request was
    # originally prepared.
    completed_at = (
        current_time
        - timedelta(seconds=30)
    )

    previous_run = AutomationRun(
        rule_id=rule.id,
        started_at=(
            completed_at
            - timedelta(seconds=5)
        ),
        completed_at=completed_at,
        trigger_value=5.8,
        status=ExecutionStatus.COMPLETED,
        result_summary="Previous execution",
        error_message=None,
    )

    test_session.add(
        previous_run
    )

    await test_session.commit()

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation rule is no longer eligible: "
            "cooldown"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=request,
            started_at=current_time,
        )

async def test_different_rules_cannot_claim_same_active_actuator(
    test_session,
):
    system = await create_system(
        test_session
    )

    first_rule = await create_rule(
        test_session,
        system,
    )

    second_rule = AutomationRule(
        system_id=system.id,
        name="Second Low pH Rule",
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
        priority=10,
        cooldown_seconds=0,
    )

    test_session.add(
        second_rule
    )

    await test_session.commit()
    await test_session.refresh(
        second_rule
    )

    await create_actuator(
        test_session,
        system,
    )

    first_request = await prepare_request(
        test_session,
        first_rule,
    )

    second_request = await prepare_request(
        test_session,
        second_rule,
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

    await create_automation_execution_records(
        test_session,
        request=first_request,
        started_at=started_at,
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation actuator already "
            "has active execution"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=second_request,
            started_at=(
                started_at
                + timedelta(milliseconds=100)
            ),
        )

    run_result = await test_session.execute(
        select(AutomationRun)
    )

    runs = list(
        run_result.scalars().all()
    )

    assert len(runs) == 1
    assert (
        runs[0].rule_id
        == first_rule.id
    )


async def test_existing_active_actuator_event_blocks_automation_claim(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    actuator = await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
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

    existing_event = ActuatorEvent(
        actuator_id=actuator.id,
        command_type=(
            ActuatorCommandType.ACTIVATE
        ),
        requested_value=1.0,
        actual_value=None,
        started_at=started_at,
        completed_at=None,
        duration_ms=None,
        trigger_source=(
            TriggerSource.MANUAL
        ),
        status=ExecutionStatus.RUNNING,
        fault_code=None,
        error_message=None,
    )

    test_session.add(
        existing_event
    )

    await test_session.commit()

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation actuator already "
            "has active execution"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=request,
            started_at=(
                started_at
                + timedelta(seconds=1)
            ),
        )

    run_result = await test_session.execute(
        select(AutomationRun).where(
            AutomationRun.rule_id
            == rule.id
        )
    )

    assert (
        run_result.scalars().all()
        == []
    )


async def test_different_rules_cannot_claim_same_active_actuator(
    test_session,
):
    system = await create_system(
        test_session
    )

    first_rule = await create_rule(
        test_session,
        system,
    )

    second_rule = AutomationRule(
        system_id=system.id,
        name="Second Low pH Rule",
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
        priority=10,
        cooldown_seconds=0,
    )

    test_session.add(
        second_rule
    )

    await test_session.commit()
    await test_session.refresh(
        second_rule
    )

    await create_actuator(
        test_session,
        system,
    )

    first_request = await prepare_request(
        test_session,
        first_rule,
    )

    second_request = await prepare_request(
        test_session,
        second_rule,
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

    await create_automation_execution_records(
        test_session,
        request=first_request,
        started_at=started_at,
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation actuator already "
            "has active execution"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=second_request,
            started_at=(
                started_at
                + timedelta(milliseconds=100)
            ),
        )

    run_result = await test_session.execute(
        select(AutomationRun)
    )

    runs = list(
        run_result.scalars().all()
    )

    assert len(runs) == 1
    assert (
        runs[0].rule_id
        == first_rule.id
    )


async def test_existing_active_actuator_event_blocks_automation_claim(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    actuator = await create_actuator(
        test_session,
        system,
    )

    request = await prepare_request(
        test_session,
        rule,
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

    existing_event = ActuatorEvent(
        actuator_id=actuator.id,
        command_type=(
            ActuatorCommandType.ACTIVATE
        ),
        requested_value=1.0,
        actual_value=None,
        started_at=started_at,
        completed_at=None,
        duration_ms=None,
        trigger_source=(
            TriggerSource.MANUAL
        ),
        status=ExecutionStatus.RUNNING,
        fault_code=None,
        error_message=None,
    )

    test_session.add(
        existing_event
    )

    await test_session.commit()

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation actuator already "
            "has active execution"
        ),
    ):
        await create_automation_execution_records(
            test_session,
            request=request,
            started_at=(
                started_at
                + timedelta(seconds=1)
            ),
        )

    run_result = await test_session.execute(
        select(AutomationRun).where(
            AutomationRun.rule_id
            == rule.id
        )
    )

    assert (
        run_result.scalars().all()
        == []
    )