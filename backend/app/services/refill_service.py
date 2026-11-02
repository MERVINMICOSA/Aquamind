from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from uuid import UUID

from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ExecutionStatus, RefillTrigger
from app.models.system import Reservoir, Tank


# ============================================================
# EXCEPTIONS
# ============================================================


class RefillCalculationError(ValueError):
    """Raised when refill event values are unsafe or inconsistent."""


# ============================================================
# DATA OBJECTS
# ============================================================


@dataclass(frozen=True, slots=True)
class RefillEventPlan:
    start_level_percent: float
    end_level_percent: float
    level_change_percent: float

    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None

    trigger: RefillTrigger
    status: ExecutionStatus
    timeout_reason: str | None

@dataclass(frozen=True, slots=True)
class RefillContext:
    reservoir: Reservoir
    target_tank: Tank
    system_id: UUID

@dataclass(frozen=True, slots=True)
class PreparedRefillPlan:
    reservoir_id: UUID
    target_tank_id: UUID
    system_id: UUID

    plan: RefillEventPlan


# ============================================================
# WATER LEVEL VALIDATION
# ============================================================


def validate_level_percent(
    value: float,
    *,
    field_name: str,
) -> float:
    numeric_value = float(value)

    if not isfinite(numeric_value):
        raise RefillCalculationError(
            f"{field_name} must be a finite number"
        )

    if numeric_value < 0 or numeric_value > 100:
        raise RefillCalculationError(
            f"{field_name} must be between 0 and 100"
        )

    return numeric_value


def calculate_level_change_percent(
    *,
    start_level_percent: float,
    end_level_percent: float,
) -> float:
    start_level = validate_level_percent(
        start_level_percent,
        field_name="Start level percent",
    )

    end_level = validate_level_percent(
        end_level_percent,
        field_name="End level percent",
    )

    return end_level - start_level


# ============================================================
# TIME / DURATION CALCULATION
# ============================================================


def calculate_refill_duration_seconds(
    *,
    started_at: datetime,
    completed_at: datetime | None,
) -> float | None:
    if started_at.tzinfo is None:
        raise RefillCalculationError(
            "Refill start time must be timezone-aware"
        )

    if completed_at is None:
        return None

    if completed_at.tzinfo is None:
        raise RefillCalculationError(
            "Refill completion time must be timezone-aware"
        )

    if completed_at < started_at:
        raise RefillCalculationError(
            "Refill completion time cannot be before start time"
        )

    return (
        completed_at - started_at
    ).total_seconds()


# ============================================================
# LIFECYCLE VALIDATION
# ============================================================


def validate_refill_lifecycle(
    *,
    status: ExecutionStatus,
    completed_at: datetime | None,
    timeout_reason: str | None,
) -> str | None:
    terminal_statuses = {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.TIMEOUT,
    }

    active_statuses = {
        ExecutionStatus.PENDING,
        ExecutionStatus.RUNNING,
    }

    if status in terminal_statuses and completed_at is None:
        raise RefillCalculationError(
            "Terminal refill status requires a completion time"
        )

    if status in active_statuses and completed_at is not None:
        raise RefillCalculationError(
            "Active refill status cannot have a completion time"
        )

    normalized_timeout_reason = (
        timeout_reason.strip()
        if timeout_reason is not None
        else None
    )

    if status == ExecutionStatus.TIMEOUT:
        if not normalized_timeout_reason:
            raise RefillCalculationError(
                "Timed out refill requires a timeout reason"
            )

        return normalized_timeout_reason

    if normalized_timeout_reason:
        raise RefillCalculationError(
            "Timeout reason is only valid for timed out refill events"
        )

    return None


# ============================================================
# REFILL EVENT PLAN
# ============================================================


def build_refill_event_plan(
    *,
    start_level_percent: float,
    end_level_percent: float,
    started_at: datetime,
    completed_at: datetime | None,
    trigger: RefillTrigger,
    status: ExecutionStatus,
    timeout_reason: str | None = None,
) -> RefillEventPlan:
    start_level = validate_level_percent(
        start_level_percent,
        field_name="Start level percent",
    )

    end_level = validate_level_percent(
        end_level_percent,
        field_name="End level percent",
    )

    level_change_percent = (
        end_level - start_level
    )

    normalized_timeout_reason = (
        validate_refill_lifecycle(
            status=status,
            completed_at=completed_at,
            timeout_reason=timeout_reason,
        )
    )

    duration_seconds = (
        calculate_refill_duration_seconds(
            started_at=started_at,
            completed_at=completed_at,
        )
    )

    return RefillEventPlan(
        start_level_percent=start_level,
        end_level_percent=end_level,
        level_change_percent=level_change_percent,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration_seconds,
        trigger=trigger,
        status=status,
        timeout_reason=normalized_timeout_reason,
    )


# ============================================================
# REFILL CONTEXT RESOLUTION
# ============================================================


async def resolve_refill_context(
    session: AsyncSession,
    *,
    reservoir_id: UUID,
    target_tank_id: UUID,
) -> RefillContext:
    # --------------------------------------------------------
    # Reservoir
    # --------------------------------------------------------

    reservoir = await session.get(
        Reservoir,
        reservoir_id,
    )

    if reservoir is None or reservoir.deleted_at is not None:
        raise RefillCalculationError(
            "Reservoir not found"
        )

    if not reservoir.is_active:
        raise RefillCalculationError(
            "Reservoir is inactive"
        )

    # --------------------------------------------------------
    # Target tank
    # --------------------------------------------------------

    target_tank = await session.get(
        Tank,
        target_tank_id,
    )

    if target_tank is None or target_tank.deleted_at is not None:
        raise RefillCalculationError(
            "Target tank not found"
        )

    if not target_tank.is_active:
        raise RefillCalculationError(
            "Target tank is inactive"
        )

    # --------------------------------------------------------
    # System relationship
    # --------------------------------------------------------

    if reservoir.system_id != target_tank.system_id:
        raise RefillCalculationError(
            "Reservoir and target tank must belong to the same system"
        )

    return RefillContext(
        reservoir=reservoir,
        target_tank=target_tank,
        system_id=reservoir.system_id,
    )


# ============================================================
# PREPARED REFILL PLAN
# ============================================================


async def prepare_refill_plan(
    session: AsyncSession,
    *,
    reservoir_id: UUID,
    target_tank_id: UUID,
    start_level_percent: float,
    end_level_percent: float,
    started_at: datetime,
    completed_at: datetime | None,
    trigger: RefillTrigger,
    status: ExecutionStatus,
    timeout_reason: str | None = None,
) -> PreparedRefillPlan:
    context = await resolve_refill_context(
        session,
        reservoir_id=reservoir_id,
        target_tank_id=target_tank_id,
    )

    plan = build_refill_event_plan(
        start_level_percent=start_level_percent,
        end_level_percent=end_level_percent,
        started_at=started_at,
        completed_at=completed_at,
        trigger=trigger,
        status=status,
        timeout_reason=timeout_reason,
    )

    return PreparedRefillPlan(
        reservoir_id=context.reservoir.id,
        target_tank_id=context.target_tank.id,
        system_id=context.system_id,
        plan=plan,
    )


# ============================================================
# REFILL CONTROL / SAFETY DECISIONS
# ============================================================


class RefillLevelAction(str, Enum):
    NONE = "none"
    SCHEDULED = "scheduled"
    IMMEDIATE = "immediate"


def validate_refill_trigger_thresholds(
    *,
    critical_low_percent: float,
    warning_low_percent: float,
) -> None:
    critical_low = validate_level_percent(
        critical_low_percent,
        field_name="Critical low threshold",
    )

    warning_low = validate_level_percent(
        warning_low_percent,
        field_name="Warning low threshold",
    )

    if critical_low >= warning_low:
        raise RefillCalculationError(
            "Critical low threshold must be below warning low threshold"
        )


def classify_refill_level(
    *,
    current_level_percent: float,
    critical_low_percent: float = 15.0,
    warning_low_percent: float = 25.0,
) -> RefillLevelAction:
    current_level = validate_level_percent(
        current_level_percent,
        field_name="Current level percent",
    )

    validate_refill_trigger_thresholds(
        critical_low_percent=critical_low_percent,
        warning_low_percent=warning_low_percent,
    )

    if current_level < critical_low_percent:
        return RefillLevelAction.IMMEDIATE

    if current_level < warning_low_percent:
        return RefillLevelAction.SCHEDULED

    return RefillLevelAction.NONE


def should_stop_refill(
    *,
    current_level_percent: float,
    target_level_percent: float = 40.0,
) -> bool:
    current_level = validate_level_percent(
        current_level_percent,
        field_name="Current level percent",
    )

    target_level = validate_level_percent(
        target_level_percent,
        field_name="Target level percent",
    )

    return current_level >= target_level


def calculate_refill_elapsed_seconds(
    *,
    started_at: datetime,
    current_time: datetime,
) -> float:
    duration = calculate_refill_duration_seconds(
        started_at=started_at,
        completed_at=current_time,
    )

    assert duration is not None

    return duration


def is_refill_timed_out(
    *,
    started_at: datetime,
    current_time: datetime,
    max_duration_seconds: float = 300.0,
) -> bool:
    max_duration = float(
        max_duration_seconds
    )

    if not isfinite(max_duration):
        raise RefillCalculationError(
            "Maximum refill duration must be a finite number"
        )

    if max_duration <= 0:
        raise RefillCalculationError(
            "Maximum refill duration must be greater than zero"
        )

    elapsed_seconds = (
        calculate_refill_elapsed_seconds(
            started_at=started_at,
            current_time=current_time,
        )
    )

    return elapsed_seconds >= max_duration


def is_refill_cooldown_active(
    *,
    last_completed_at: datetime | None,
    current_time: datetime,
    cooldown_seconds: float = 1800.0,
) -> bool:
    cooldown = float(
        cooldown_seconds
    )

    if not isfinite(cooldown):
        raise RefillCalculationError(
            "Refill cooldown must be a finite number"
        )

    if cooldown < 0:
        raise RefillCalculationError(
            "Refill cooldown cannot be negative"
        )

    if current_time.tzinfo is None:
        raise RefillCalculationError(
            "Current time must be timezone-aware"
        )

    if last_completed_at is None:
        return False

    if last_completed_at.tzinfo is None:
        raise RefillCalculationError(
            "Last refill completion time must be timezone-aware"
        )

    if current_time < last_completed_at:
        raise RefillCalculationError(
            "Current time cannot be before last refill completion time"
        )

    elapsed_seconds = (
        current_time - last_completed_at
    ).total_seconds()

    return elapsed_seconds < cooldown


def validate_refill_start_preconditions(
    *,
    refill_active: bool,
    reservoir_has_water: bool,
) -> None:
    if refill_active:
        raise RefillCalculationError(
            "Refill is already active"
        )

    if not reservoir_has_water:
        raise RefillCalculationError(
            "Reservoir does not have enough water for refill"
        )