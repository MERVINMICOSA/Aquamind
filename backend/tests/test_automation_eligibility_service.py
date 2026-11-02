from datetime import datetime, timedelta, timezone
from uuid import UUID

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
    calculate_automation_cooldown_remaining_seconds,
    evaluate_automation_rule_eligibility,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# HELPERS
# ============================================================


async def create_system(
    session,
    *,
    name="Automation Eligibility System",
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
    enabled=True,
    priority=10,
    cooldown_seconds=300,
):
    rule = AutomationRule(
        system_id=system.id,
        name="Low pH Pump Rule",
        description=(
            "Activate pump when pH is too low."
        ),
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
# PURE COOLDOWN CALCULATION
# ============================================================


async def test_no_previous_completion_has_no_cooldown():
    current_time = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    remaining = (
        calculate_automation_cooldown_remaining_seconds(
            last_completed_at=None,
            current_time=current_time,
            cooldown_seconds=300,
        )
    )

    assert remaining == pytest.approx(0.0)


async def test_cooldown_remaining_is_calculated():
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
        - timedelta(seconds=120)
    )

    remaining = (
        calculate_automation_cooldown_remaining_seconds(
            last_completed_at=completed_at,
            current_time=current_time,
            cooldown_seconds=300,
        )
    )

    assert remaining == pytest.approx(180.0)


async def test_naive_current_time_is_rejected():
    with pytest.raises(
        AutomationServiceError,
        match="Current time must be timezone-aware",
    ):
        calculate_automation_cooldown_remaining_seconds(
            last_completed_at=None,
            current_time=datetime(
                2026,
                1,
                1,
                12,
                0,
                0,
            ),
            cooldown_seconds=300,
        )


# ============================================================
# RULE ELIGIBILITY
# ============================================================


async def test_rule_without_history_is_eligible(
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

    result = (
        await evaluate_automation_rule_eligibility(
            test_session,
            rule_id=rule.id,
            current_time=current_time,
        )
    )

    assert result.rule_id == rule.id
    assert result.eligible is True

    assert (
        result.reason
        == AutomationEligibilityReason.ELIGIBLE
    )

    assert result.priority == 10

    assert (
        result.cooldown_remaining_seconds
        == pytest.approx(0.0)
    )

    assert result.last_completed_at is None
    assert result.active_run_id is None


async def test_disabled_rule_is_not_eligible(
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
        await evaluate_automation_rule_eligibility(
            test_session,
            rule_id=rule.id,
            current_time=datetime.now(
                timezone.utc
            ),
        )
    )

    assert result.eligible is False

    assert (
        result.reason
        == AutomationEligibilityReason.DISABLED
    )


async def test_active_run_blocks_rule(
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

    active_run = await create_run(
        test_session,
        rule,
        started_at=(
            current_time
            - timedelta(seconds=30)
        ),
        status=ExecutionStatus.RUNNING,
    )

    result = (
        await evaluate_automation_rule_eligibility(
            test_session,
            rule_id=rule.id,
            current_time=current_time,
        )
    )

    assert result.eligible is False

    assert (
        result.reason
        == AutomationEligibilityReason.RUN_ACTIVE
    )

    assert (
        result.active_run_id
        == active_run.id
    )


async def test_recent_terminal_run_enforces_cooldown(
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
        - timedelta(seconds=120)
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
        await evaluate_automation_rule_eligibility(
            test_session,
            rule_id=rule.id,
            current_time=current_time,
        )
    )

    assert result.eligible is False

    assert (
        result.reason
        == AutomationEligibilityReason.COOLDOWN
    )

    assert (
        result.cooldown_remaining_seconds
        == pytest.approx(180.0)
    )


async def test_rule_becomes_eligible_when_cooldown_expires(
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
        - timedelta(seconds=300)
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
        await evaluate_automation_rule_eligibility(
            test_session,
            rule_id=rule.id,
            current_time=current_time,
        )
    )

    assert result.eligible is True

    assert (
        result.reason
        == AutomationEligibilityReason.ELIGIBLE
    )

    assert (
        result.cooldown_remaining_seconds
        == pytest.approx(0.0)
    )


async def test_failed_run_also_enforces_cooldown(
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
            - timedelta(seconds=5)
        ),
        completed_at=completed_at,
        status=ExecutionStatus.FAILED,
    )

    result = (
        await evaluate_automation_rule_eligibility(
            test_session,
            rule_id=rule.id,
            current_time=current_time,
        )
    )

    assert result.eligible is False

    assert (
        result.reason
        == AutomationEligibilityReason.COOLDOWN
    )

    assert (
        result.cooldown_remaining_seconds
        == pytest.approx(240.0)
    )


async def test_zero_cooldown_allows_immediate_next_run(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
        cooldown_seconds=0,
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
        completed_at=current_time,
        status=ExecutionStatus.COMPLETED,
    )

    result = (
        await evaluate_automation_rule_eligibility(
            test_session,
            rule_id=rule.id,
            current_time=current_time,
        )
    )

    assert result.eligible is True

    assert (
        result.reason
        == AutomationEligibilityReason.ELIGIBLE
    )