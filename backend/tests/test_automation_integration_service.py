from datetime import datetime, timedelta, timezone

import pytest

from app.db.enums import (
    AutomationTriggerType,
    ExecutionStatus,
)
from app.models.automation import (
    AutomationRule,
    AutomationRun,
)
from app.models.system import AquaponicsSystem
from app.services.automation_service import (
    AutomationEligibilityReason,
    AutomationServiceError,
    PreparedAutomationDecision,
    prepare_sensor_threshold_automation_decision,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# HELPERS
# ============================================================


async def create_system(
    session,
    *,
    name="Automation Integration System",
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
    *,
    trigger_type=AutomationTriggerType.SENSOR_THRESHOLD,
    enabled=True,
    priority=10,
    cooldown_seconds=300,
    condition_definition=None,
    action_definition=None,
):
    rule = AutomationRule(
        system_id=system.id,
        name="Low pH Pump Rule",
        description=(
            "Activate pump when pH becomes too low."
        ),
        trigger_type=trigger_type,
        condition_definition=(
            condition_definition
            if condition_definition is not None
            else {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "less_than",
                "value": 6.0,
            }
        ),
        action_definition=(
            action_definition
            if action_definition is not None
            else {
                "action": "activate_actuator",
                "actuator_type": "water_pump",
                "value": 1.0,
            }
        ),
        enabled=enabled,
        priority=priority,
        cooldown_seconds=cooldown_seconds,
    )

    session.add(rule)

    await session.commit()
    await session.refresh(rule)

    return rule


async def create_run(
    session,
    rule,
    *,
    started_at,
    completed_at=None,
    status=ExecutionStatus.RUNNING,
):
    run = AutomationRun(
        rule_id=rule.id,
        started_at=started_at,
        completed_at=completed_at,
        trigger_value=5.8,
        status=status,
        result_summary=None,
        error_message=None,
    )

    session.add(run)

    await session.commit()
    await session.refresh(run)

    return run


# ============================================================
# MATCHED DECISION
# ============================================================


async def test_matching_eligible_rule_prepares_action(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
        priority=20,
    )

    result = (
        await prepare_sensor_threshold_automation_decision(
            test_session,
            rule_id=rule.id,
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=5.8,
            current_time=datetime.now(
                timezone.utc
            ),
        )
    )

    assert isinstance(
        result,
        PreparedAutomationDecision,
    )

    assert result.rule_id == rule.id

    assert result.should_execute is True
    assert result.condition_matched is True

    assert result.priority == 20

    assert (
        result.trigger_value
        == pytest.approx(5.8)
    )

    assert result.eligibility.eligible is True

    assert (
        result.eligibility.reason
        == AutomationEligibilityReason.ELIGIBLE
    )

    assert result.action is not None

    assert (
        result.action.action
        == "activate_actuator"
    )

    assert (
        result.action.actuator_type
        == "water_pump"
    )

    assert (
        result.action.value
        == pytest.approx(1.0)
    )


# ============================================================
# CONDITION DOES NOT MATCH
# ============================================================


async def test_threshold_not_crossed_does_not_prepare_action(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    result = (
        await prepare_sensor_threshold_automation_decision(
            test_session,
            rule_id=rule.id,
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=6.5,
            current_time=datetime.now(
                timezone.utc
            ),
        )
    )

    assert result.should_execute is False
    assert result.condition_matched is False
    assert result.action is None

    assert result.eligibility.eligible is True


async def test_different_sensor_does_not_prepare_action(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    result = (
        await prepare_sensor_threshold_automation_decision(
            test_session,
            rule_id=rule.id,
            sensor_type="tds",
            measurement_type="ph",
            trigger_value=5.0,
            current_time=datetime.now(
                timezone.utc
            ),
        )
    )

    assert result.should_execute is False
    assert result.condition_matched is False
    assert result.action is None


# ============================================================
# ELIGIBILITY BLOCKS EXECUTION
# ============================================================


async def test_disabled_rule_does_not_prepare_action(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
        enabled=False,
    )

    result = (
        await prepare_sensor_threshold_automation_decision(
            test_session,
            rule_id=rule.id,
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=5.5,
            current_time=datetime.now(
                timezone.utc
            ),
        )
    )

    assert result.should_execute is False
    assert result.condition_matched is False
    assert result.action is None

    assert (
        result.eligibility.reason
        == AutomationEligibilityReason.DISABLED
    )


async def test_active_run_blocks_prepared_action(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
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

    await create_run(
        test_session,
        rule,
        started_at=(
            current_time
            - timedelta(seconds=10)
        ),
        status=ExecutionStatus.RUNNING,
    )

    result = (
        await prepare_sensor_threshold_automation_decision(
            test_session,
            rule_id=rule.id,
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=5.5,
            current_time=current_time,
        )
    )

    assert result.should_execute is False
    assert result.action is None

    assert (
        result.eligibility.reason
        == AutomationEligibilityReason.RUN_ACTIVE
    )


async def test_cooldown_blocks_prepared_action(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
        cooldown_seconds=300,
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

    completed_at = (
        current_time
        - timedelta(seconds=60)
    )

    await create_run(
        test_session,
        rule,
        started_at=(
            completed_at
            - timedelta(seconds=10)
        ),
        completed_at=completed_at,
        status=ExecutionStatus.COMPLETED,
    )

    result = (
        await prepare_sensor_threshold_automation_decision(
            test_session,
            rule_id=rule.id,
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=5.5,
            current_time=current_time,
        )
    )

    assert result.should_execute is False
    assert result.action is None

    assert (
        result.eligibility.reason
        == AutomationEligibilityReason.COOLDOWN
    )

    assert (
        result.eligibility.cooldown_remaining_seconds
        == pytest.approx(240.0)
    )


# ============================================================
# TRIGGER TYPE VALIDATION
# ============================================================


async def test_non_sensor_threshold_rule_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
        trigger_type=AutomationTriggerType.SCHEDULE,
    )

    with pytest.raises(
        AutomationServiceError,
        match=(
            "Automation rule is not "
            "a sensor-threshold rule"
        ),
    ):
        await prepare_sensor_threshold_automation_decision(
            test_session,
            rule_id=rule.id,
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=5.5,
            current_time=datetime.now(
                timezone.utc
            ),
        )


# ============================================================
# ACTION VALIDATION AFTER MATCH
# ============================================================


async def test_matching_rule_with_invalid_action_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
        action_definition={
            "action": "unsupported_action",
            "actuator_type": "water_pump",
            "value": 1.0,
        },
    )

    with pytest.raises(
        AutomationServiceError,
        match="Unsupported automation action",
    ):
        await prepare_sensor_threshold_automation_decision(
            test_session,
            rule_id=rule.id,
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=5.5,
            current_time=datetime.now(
                timezone.utc
            ),
        )