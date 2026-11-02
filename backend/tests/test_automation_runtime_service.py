from __future__ import annotations

from uuid import uuid4

import pytest

from app.db.enums import (
    ActuatorCommandType,
    ActuatorState,
    ActuatorType,
    AutomationTriggerType,
    ControlMode,
    TriggerSource,
)
from app.models.actuators import Actuator
from app.models.automation import AutomationRule
from app.models.system import AquaponicsSystem
from app.services.automation_runtime_service import (
    AutomationRuntimeServiceError,
    prepare_automation_execution_request,
)
from app.services.automation_service import (
    AutomationEligibilityReason,
    AutomationRuleEligibility,
    PreparedAutomationAction,
    PreparedAutomationDecision,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# HELPERS
# ============================================================


async def create_system(
    session,
    *,
    name="Automation Runtime System",
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
        name="Low pH Pump Rule",
        description=(
            "Activate water pump when pH is low."
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
    *,
    name="Runtime Water Pump",
    actuator_type=ActuatorType.WATER_PUMP,
    control_mode=ControlMode.AUTOMATIC,
    is_enabled=True,
    deleted_at=None,
):
    actuator = Actuator(
        system_id=system.id,
        name=name,
        actuator_type=actuator_type,
        control_mode=control_mode,
        hardware_identifier=None,
        location_type=None,
        location_id=None,
        is_enabled=is_enabled,
        safety_config=None,
        current_state=ActuatorState.OFF,
        current_value=None,
        last_state_at=None,
        deleted_at=deleted_at,
    )

    session.add(actuator)

    await session.commit()
    await session.refresh(actuator)

    return actuator


def executable_decision(
    rule,
    *,
    actuator_type="water_pump",
):
    eligibility = AutomationRuleEligibility(
        rule_id=rule.id,
        eligible=True,
        reason=(
            AutomationEligibilityReason.ELIGIBLE
        ),
        priority=20,
        cooldown_remaining_seconds=0.0,
        last_completed_at=None,
        active_run_id=None,
    )

    return PreparedAutomationDecision(
        rule_id=rule.id,
        should_execute=True,
        condition_matched=True,
        priority=20,
        trigger_value=5.8,
        eligibility=eligibility,
        action=PreparedAutomationAction(
            action="activate_actuator",
            actuator_type=actuator_type,
            value=1.0,
        ),
    )


# ============================================================
# SUCCESSFUL RESOLUTION
# ============================================================


async def test_prepares_execution_request_for_matching_actuator(
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

    request = (
        await prepare_automation_execution_request(
            test_session,
            decision=executable_decision(
                rule
            ),
        )
    )

    assert request.rule_id == rule.id
    assert request.system_id == system.id

    assert (
        request.actuator_id
        == actuator.id
    )

    assert (
        request.actuator_type
        == ActuatorType.WATER_PUMP
    )

    assert (
        request.command_type
        == ActuatorCommandType.ACTIVATE
    )

    assert (
        request.requested_value
        == pytest.approx(1.0)
    )

    assert (
        request.trigger_source
        == TriggerSource.AUTOMATION
    )

    assert (
        request.trigger_value
        == pytest.approx(5.8)
    )

    assert request.priority == 20


# ============================================================
# DECISION BOUNDARY
# ============================================================


async def test_non_executable_decision_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    decision = executable_decision(
        rule
    )

    decision = PreparedAutomationDecision(
        rule_id=decision.rule_id,
        should_execute=False,
        condition_matched=False,
        priority=decision.priority,
        trigger_value=decision.trigger_value,
        eligibility=decision.eligibility,
        action=None,
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation decision is not executable"
        ),
    ):
        await prepare_automation_execution_request(
            test_session,
            decision=decision,
        )


# ============================================================
# ACTUATOR ELIGIBILITY
# ============================================================


async def test_ineligible_actuators_are_not_selected(
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
        name="Manual Pump",
        control_mode=ControlMode.MANUAL,
    )

    await create_actuator(
        test_session,
        system,
        name="Disabled Pump",
        is_enabled=False,
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "No eligible actuator found "
            "for automation action"
        ),
    ):
        await prepare_automation_execution_request(
            test_session,
            decision=executable_decision(
                rule
            ),
        )


async def test_matching_actuator_must_belong_to_rule_system(
    test_session,
):
    target_system = await create_system(
        test_session,
        name="Target System",
    )

    other_system = await create_system(
        test_session,
        name="Other System",
    )

    rule = await create_rule(
        test_session,
        target_system,
    )

    await create_actuator(
        test_session,
        other_system,
        name="Other System Pump",
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "No eligible actuator found "
            "for automation action"
        ),
    ):
        await prepare_automation_execution_request(
            test_session,
            decision=executable_decision(
                rule
            ),
        )


async def test_multiple_matching_actuators_are_rejected_as_ambiguous(
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
        name="Water Pump A",
    )

    await create_actuator(
        test_session,
        system,
        name="Water Pump B",
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Automation actuator target "
            "is ambiguous"
        ),
    ):
        await prepare_automation_execution_request(
            test_session,
            decision=executable_decision(
                rule
            ),
        )


# ============================================================
# ACTION VALIDATION
# ============================================================


async def test_unknown_actuator_type_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    rule = await create_rule(
        test_session,
        system,
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match=(
            "Unsupported automation actuator type"
        ),
    ):
        await prepare_automation_execution_request(
            test_session,
            decision=executable_decision(
                rule,
                actuator_type=(
                    "unsupported_actuator"
                ),
            ),
        )


async def test_missing_rule_is_rejected(
    test_session,
):
    eligibility = AutomationRuleEligibility(
        rule_id=uuid4(),
        eligible=True,
        reason=(
            AutomationEligibilityReason.ELIGIBLE
        ),
        priority=10,
        cooldown_remaining_seconds=0.0,
        last_completed_at=None,
        active_run_id=None,
    )

    decision = PreparedAutomationDecision(
        rule_id=eligibility.rule_id,
        should_execute=True,
        condition_matched=True,
        priority=10,
        trigger_value=5.8,
        eligibility=eligibility,
        action=PreparedAutomationAction(
            action="activate_actuator",
            actuator_type="water_pump",
            value=1.0,
        ),
    )

    with pytest.raises(
        AutomationRuntimeServiceError,
        match="Automation rule not found",
    ):
        await prepare_automation_execution_request(
            test_session,
            decision=decision,
        )