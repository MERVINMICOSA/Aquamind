from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    AutomationTriggerType,
    ExecutionStatus,
)

from app.models.automation import (
    AutomationRule,
    AutomationRun,
)


# ============================================================
# EXCEPTIONS
# ============================================================


class AutomationServiceError(ValueError):
    """Raised when automation business logic is invalid."""


# ============================================================
# DATA OBJECTS
# ============================================================


@dataclass(frozen=True, slots=True)
class SensorThresholdCondition:
    sensor_type: str
    measurement_type: str
    operator: str
    threshold_value: float


class AutomationEligibilityReason(str, Enum):
    ELIGIBLE = "eligible"
    DISABLED = "disabled"
    RUN_ACTIVE = "run_active"
    COOLDOWN = "cooldown"


@dataclass(frozen=True, slots=True)
class AutomationRuleEligibility:
    rule_id: UUID
    eligible: bool
    reason: AutomationEligibilityReason

    priority: int

    cooldown_remaining_seconds: float
    last_completed_at: datetime | None
    active_run_id: UUID | None


@dataclass(frozen=True, slots=True)
class AutomationRunPlan:
    started_at: datetime
    completed_at: datetime | None

    trigger_value: float | None

    status: ExecutionStatus

    duration_seconds: float | None

    result_summary: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class PreparedAutomationAction:
    action: str
    actuator_type: str
    value: float

@dataclass(frozen=True, slots=True)
class PreparedAutomationDecision:
    rule_id: UUID

    should_execute: bool
    condition_matched: bool

    priority: int
    trigger_value: float

    eligibility: AutomationRuleEligibility
    action: PreparedAutomationAction | None


# ============================================================
# CONSTANTS
# ============================================================


SUPPORTED_THRESHOLD_OPERATORS = {
    "less_than",
    "greater_than",
}


SUPPORTED_AUTOMATION_ACTIONS = {
    "activate_actuator",
}


ACTIVE_AUTOMATION_STATUSES = {
    ExecutionStatus.PENDING,
    ExecutionStatus.RUNNING,
}


TERMINAL_AUTOMATION_STATUSES = {
    ExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
    ExecutionStatus.TIMEOUT,
}


# ============================================================
# INTERNAL VALIDATION
# ============================================================


def _require_non_empty_string(
    definition: dict[str, Any],
    *,
    key: str,
) -> str:
    value = definition.get(key)

    if not isinstance(value, str):
        raise AutomationServiceError(
            f"{key} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise AutomationServiceError(
            f"{key} cannot be empty"
        )

    return normalized


def _require_finite_number(
    value: Any,
    *,
    field_name: str,
) -> float:
    if isinstance(value, bool):
        raise AutomationServiceError(
            f"{field_name} must be a number"
        )

    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise AutomationServiceError(
            f"{field_name} must be a number"
        ) from exc

    if not isfinite(numeric_value):
        raise AutomationServiceError(
            f"{field_name} must be a finite number"
        )

    return numeric_value


def _require_timezone_aware_datetime(
    value: datetime,
    *,
    field_name: str,
) -> datetime:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise AutomationServiceError(
            f"{field_name} must be timezone-aware"
        )

    return value


# ============================================================
# SENSOR THRESHOLD CONDITION PARSING
# ============================================================


def parse_sensor_threshold_condition(
    condition_definition: dict[str, Any],
) -> SensorThresholdCondition:
    if not isinstance(
        condition_definition,
        dict,
    ):
        raise AutomationServiceError(
            "Sensor threshold condition must be an object"
        )

    sensor_type = _require_non_empty_string(
        condition_definition,
        key="sensor_type",
    )

    measurement_type = _require_non_empty_string(
        condition_definition,
        key="measurement_type",
    )

    operator = _require_non_empty_string(
        condition_definition,
        key="operator",
    )

    if operator not in SUPPORTED_THRESHOLD_OPERATORS:
        raise AutomationServiceError(
            "Unsupported sensor threshold operator"
        )

    if "value" not in condition_definition:
        raise AutomationServiceError(
            "Sensor threshold condition requires value"
        )

    threshold_value = _require_finite_number(
        condition_definition["value"],
        field_name="Threshold value",
    )

    return SensorThresholdCondition(
        sensor_type=sensor_type,
        measurement_type=measurement_type,
        operator=operator,
        threshold_value=threshold_value,
    )


# ============================================================
# SENSOR THRESHOLD CONDITION EVALUATION
# ============================================================


def evaluate_sensor_threshold_condition(
    condition_definition: dict[str, Any],
    *,
    sensor_type: str,
    measurement_type: str,
    trigger_value: float,
) -> bool:
    condition = (
        parse_sensor_threshold_condition(
            condition_definition
        )
    )

    actual_sensor_type = sensor_type.strip()

    if not actual_sensor_type:
        raise AutomationServiceError(
            "Trigger sensor type cannot be empty"
        )

    actual_measurement_type = (
        measurement_type.strip()
    )

    if not actual_measurement_type:
        raise AutomationServiceError(
            "Trigger measurement type cannot be empty"
        )

    actual_value = _require_finite_number(
        trigger_value,
        field_name="Trigger value",
    )

    # A reading from another sensor does not make
    # the rule invalid. It simply does not match.
    if (
        actual_sensor_type
        != condition.sensor_type
    ):
        return False

    if (
        actual_measurement_type
        != condition.measurement_type
    ):
        return False

    if condition.operator == "less_than":
        return (
            actual_value
            < condition.threshold_value
        )

    if condition.operator == "greater_than":
        return (
            actual_value
            > condition.threshold_value
        )

    # Defensive fallback.
    raise AutomationServiceError(
        "Unsupported sensor threshold operator"
    )


# ============================================================
# AUTOMATION COOLDOWN
# ============================================================


def calculate_automation_cooldown_remaining_seconds(
    *,
    last_completed_at: datetime | None,
    current_time: datetime,
    cooldown_seconds: int | float,
) -> float:
    current = _require_timezone_aware_datetime(
        current_time,
        field_name="Current time",
    )

    cooldown = _require_finite_number(
        cooldown_seconds,
        field_name="Cooldown seconds",
    )

    if cooldown < 0:
        raise AutomationServiceError(
            "Cooldown seconds cannot be negative"
        )

    if last_completed_at is None:
        return 0.0

    completed = _require_timezone_aware_datetime(
        last_completed_at,
        field_name="Last completion time",
    )

    if current < completed:
        raise AutomationServiceError(
            "Current time cannot be before last completion time"
        )

    elapsed_seconds = (
        current - completed
    ).total_seconds()

    remaining_seconds = (
        cooldown - elapsed_seconds
    )

    return max(
        0.0,
        remaining_seconds,
    )


# ============================================================
# DATABASE-AWARE RULE ELIGIBILITY
# ============================================================


async def evaluate_automation_rule_eligibility(
    session: AsyncSession,
    *,
    rule_id: UUID,
    current_time: datetime | None = None,
) -> AutomationRuleEligibility:
    evaluation_time = (
        current_time
        or datetime.now(timezone.utc)
    )

    _require_timezone_aware_datetime(
        evaluation_time,
        field_name="Current time",
    )

    # --------------------------------------------------------
    # Rule
    # --------------------------------------------------------

    rule = await session.get(
        AutomationRule,
        rule_id,
    )

    if rule is None:
        raise AutomationServiceError(
            "Automation rule not found"
        )

    # --------------------------------------------------------
    # Enabled state
    # --------------------------------------------------------

    if not rule.enabled:
        return AutomationRuleEligibility(
            rule_id=rule.id,
            eligible=False,
            reason=(
                AutomationEligibilityReason.DISABLED
            ),
            priority=rule.priority,
            cooldown_remaining_seconds=0.0,
            last_completed_at=None,
            active_run_id=None,
        )

    # --------------------------------------------------------
    # Prevent overlapping execution
    # --------------------------------------------------------

    active_run_result = await session.execute(
        select(AutomationRun)
        .where(
            AutomationRun.rule_id == rule.id,
            AutomationRun.status.in_(
                (
                    ExecutionStatus.PENDING,
                    ExecutionStatus.RUNNING,
                )
            ),
        )
        .order_by(
            AutomationRun.started_at.desc()
        )
        .limit(1)
    )

    active_run = (
        active_run_result.scalars().first()
    )

    if active_run is not None:
        return AutomationRuleEligibility(
            rule_id=rule.id,
            eligible=False,
            reason=(
                AutomationEligibilityReason.RUN_ACTIVE
            ),
            priority=rule.priority,
            cooldown_remaining_seconds=0.0,
            last_completed_at=None,
            active_run_id=active_run.id,
        )

    # --------------------------------------------------------
    # Latest terminal execution
    # --------------------------------------------------------

    terminal_statuses = (
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.TIMEOUT,
    )

    latest_run_result = await session.execute(
        select(AutomationRun)
        .where(
            AutomationRun.rule_id == rule.id,
            AutomationRun.status.in_(
                terminal_statuses
            ),
            AutomationRun.completed_at.is_not(
                None
            ),
        )
        .order_by(
            AutomationRun.completed_at.desc()
        )
        .limit(1)
    )

    latest_run = (
        latest_run_result.scalars().first()
    )

    last_completed_at = (
        latest_run.completed_at
        if latest_run is not None
        else None
    )

    # SQLite test environments can return TIMESTAMPTZ
    # values without tzinfo. The persisted field represents
    # an absolute timestamp, so normalize that boundary.
    if (
        last_completed_at is not None
        and last_completed_at.tzinfo is None
    ):
        last_completed_at = (
            last_completed_at.replace(
                tzinfo=timezone.utc
            )
        )

    cooldown_remaining_seconds = (
        calculate_automation_cooldown_remaining_seconds(
            last_completed_at=last_completed_at,
            current_time=evaluation_time,
            cooldown_seconds=rule.cooldown_seconds,
        )
    )

    if cooldown_remaining_seconds > 0:
        return AutomationRuleEligibility(
            rule_id=rule.id,
            eligible=False,
            reason=(
                AutomationEligibilityReason.COOLDOWN
            ),
            priority=rule.priority,
            cooldown_remaining_seconds=(
                cooldown_remaining_seconds
            ),
            last_completed_at=last_completed_at,
            active_run_id=None,
        )

    # --------------------------------------------------------
    # Eligible
    # --------------------------------------------------------

    return AutomationRuleEligibility(
        rule_id=rule.id,
        eligible=True,
        reason=(
            AutomationEligibilityReason.ELIGIBLE
        ),
        priority=rule.priority,
        cooldown_remaining_seconds=0.0,
        last_completed_at=last_completed_at,
        active_run_id=None,
    )


# ============================================================
# AUTOMATION RUN DURATION
# ============================================================


def calculate_automation_run_duration_seconds(
    *,
    started_at: datetime,
    completed_at: datetime | None,
) -> float | None:
    started = _require_timezone_aware_datetime(
        started_at,
        field_name="Automation run start time",
    )

    if completed_at is None:
        return None

    completed = _require_timezone_aware_datetime(
        completed_at,
        field_name="Automation run completion time",
    )

    if completed < started:
        raise AutomationServiceError(
            "Automation run completion time cannot be before start time"
        )

    return (
        completed - started
    ).total_seconds()


# ============================================================
# AUTOMATION RUN LIFECYCLE
# ============================================================


def validate_automation_run_lifecycle(
    *,
    status: ExecutionStatus,
    started_at: datetime,
    completed_at: datetime | None,
) -> float | None:
    _require_timezone_aware_datetime(
        started_at,
        field_name="Automation run start time",
    )

    if status in ACTIVE_AUTOMATION_STATUSES:
        if completed_at is not None:
            raise AutomationServiceError(
                "Active automation run cannot have a completion time"
            )

    elif status in TERMINAL_AUTOMATION_STATUSES:
        if completed_at is None:
            raise AutomationServiceError(
                "Terminal automation run requires a completion time"
            )

    else:
        raise AutomationServiceError(
            "Unsupported automation run status"
        )

    return calculate_automation_run_duration_seconds(
        started_at=started_at,
        completed_at=completed_at,
    )


# ============================================================
# AUTOMATION TRIGGER VALUE
# ============================================================


def validate_automation_trigger_value(
    trigger_value: float | None,
) -> float | None:
    if trigger_value is None:
        return None

    return _require_finite_number(
        trigger_value,
        field_name="Automation trigger value",
    )


# ============================================================
# AUTOMATION RUN PLAN
# ============================================================


def build_automation_run_plan(
    *,
    started_at: datetime,
    completed_at: datetime | None,
    trigger_value: float | None,
    status: ExecutionStatus,
    result_summary: str | None = None,
    error_message: str | None = None,
) -> AutomationRunPlan:
    duration_seconds = (
        validate_automation_run_lifecycle(
            status=status,
            started_at=started_at,
            completed_at=completed_at,
        )
    )

    normalized_trigger_value = (
        validate_automation_trigger_value(
            trigger_value
        )
    )

    return AutomationRunPlan(
        started_at=started_at,
        completed_at=completed_at,
        trigger_value=normalized_trigger_value,
        status=status,
        duration_seconds=duration_seconds,
        result_summary=result_summary,
        error_message=error_message,
    )


# ============================================================
# AUTOMATION ACTION DEFINITION
# ============================================================


def parse_automation_action_definition(
    action_definition: dict[str, Any],
) -> PreparedAutomationAction:
    if not isinstance(
        action_definition,
        dict,
    ):
        raise AutomationServiceError(
            "Automation action definition must be an object"
        )

    action = _require_non_empty_string(
        action_definition,
        key="action",
    )

    if action not in SUPPORTED_AUTOMATION_ACTIONS:
        raise AutomationServiceError(
            "Unsupported automation action"
        )

    actuator_type = _require_non_empty_string(
        action_definition,
        key="actuator_type",
    )

    if "value" not in action_definition:
        raise AutomationServiceError(
            "Automation action requires value"
        )

    value = _require_finite_number(
        action_definition["value"],
        field_name="Automation action value",
    )

    return PreparedAutomationAction(
        action=action,
        actuator_type=actuator_type,
        value=value,
    )


# ============================================================
# SENSOR-THRESHOLD AUTOMATION DECISION
# ============================================================


async def prepare_sensor_threshold_automation_decision(
    session: AsyncSession,
    *,
    rule_id: UUID,
    sensor_type: str,
    measurement_type: str,
    trigger_value: float,
    current_time: datetime | None = None,
) -> PreparedAutomationDecision:
    actual_trigger_value = _require_finite_number(
        trigger_value,
        field_name="Trigger value",
    )

    # --------------------------------------------------------
    # Rule
    # --------------------------------------------------------

    rule = await session.get(
        AutomationRule,
        rule_id,
    )

    if rule is None:
        raise AutomationServiceError(
            "Automation rule not found"
        )

    if (
        rule.trigger_type
        != AutomationTriggerType.SENSOR_THRESHOLD
    ):
        raise AutomationServiceError(
            "Automation rule is not a sensor-threshold rule"
        )

    # --------------------------------------------------------
    # Eligibility
    # --------------------------------------------------------

    eligibility = (
        await evaluate_automation_rule_eligibility(
            session,
            rule_id=rule.id,
            current_time=current_time,
        )
    )

    if not eligibility.eligible:
        return PreparedAutomationDecision(
            rule_id=rule.id,
            should_execute=False,
            condition_matched=False,
            priority=rule.priority,
            trigger_value=actual_trigger_value,
            eligibility=eligibility,
            action=None,
        )

    # --------------------------------------------------------
    # Condition
    # --------------------------------------------------------

    condition_matched = (
        evaluate_sensor_threshold_condition(
            rule.condition_definition,
            sensor_type=sensor_type,
            measurement_type=measurement_type,
            trigger_value=actual_trigger_value,
        )
    )

    if not condition_matched:
        return PreparedAutomationDecision(
            rule_id=rule.id,
            should_execute=False,
            condition_matched=False,
            priority=rule.priority,
            trigger_value=actual_trigger_value,
            eligibility=eligibility,
            action=None,
        )

    # --------------------------------------------------------
    # Action
    # --------------------------------------------------------

    action = parse_automation_action_definition(
        rule.action_definition
    )

    return PreparedAutomationDecision(
        rule_id=rule.id,
        should_execute=True,
        condition_matched=True,
        priority=rule.priority,
        trigger_value=actual_trigger_value,
        eligibility=eligibility,
        action=action,
    )