from datetime import datetime, timedelta, timezone

import pytest

from app.db.enums import ExecutionStatus, RefillTrigger
from app.services.refill_service import (
    RefillCalculationError,
    build_refill_event_plan,
    calculate_level_change_percent,
    calculate_refill_duration_seconds,
    validate_level_percent,
    validate_refill_lifecycle,
)


# ============================================================
# LEVEL VALIDATION
# ============================================================


def test_level_percent_accepts_valid_boundaries():
    assert (
        validate_level_percent(
            0.0,
            field_name="Level",
        )
        == 0.0
    )

    assert (
        validate_level_percent(
            100.0,
            field_name="Level",
        )
        == 100.0
    )


def test_level_percent_rejects_value_below_zero():
    with pytest.raises(
        RefillCalculationError,
        match="Start level percent must be between 0 and 100",
    ):
        validate_level_percent(
            -0.1,
            field_name="Start level percent",
        )


def test_level_percent_rejects_value_above_one_hundred():
    with pytest.raises(
        RefillCalculationError,
        match="End level percent must be between 0 and 100",
    ):
        validate_level_percent(
            100.1,
            field_name="End level percent",
        )


def test_level_percent_rejects_non_finite_value():
    with pytest.raises(
        RefillCalculationError,
        match="Level must be a finite number",
    ):
        validate_level_percent(
            float("nan"),
            field_name="Level",
        )


# ============================================================
# LEVEL CHANGE
# ============================================================


def test_calculate_level_change_percent():
    result = calculate_level_change_percent(
        start_level_percent=25.0,
        end_level_percent=70.0,
    )

    assert result == pytest.approx(45.0)


def test_level_change_can_be_negative():
    result = calculate_level_change_percent(
        start_level_percent=70.0,
        end_level_percent=65.0,
    )

    assert result == pytest.approx(-5.0)


# ============================================================
# DURATION
# ============================================================


def test_calculate_refill_duration_seconds():
    started_at = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    completed_at = (
        started_at
        + timedelta(seconds=90)
    )

    result = calculate_refill_duration_seconds(
        started_at=started_at,
        completed_at=completed_at,
    )

    assert result == pytest.approx(90.0)


def test_running_refill_has_no_duration():
    started_at = datetime.now(
        timezone.utc
    )

    result = calculate_refill_duration_seconds(
        started_at=started_at,
        completed_at=None,
    )

    assert result is None


def test_refill_duration_requires_timezone_aware_start():
    started_at = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
    )

    with pytest.raises(
        RefillCalculationError,
        match="Refill start time must be timezone-aware",
    ):
        calculate_refill_duration_seconds(
            started_at=started_at,
            completed_at=None,
        )


def test_refill_duration_rejects_completion_before_start():
    started_at = datetime.now(
        timezone.utc
    )

    completed_at = (
        started_at
        - timedelta(seconds=1)
    )

    with pytest.raises(
        RefillCalculationError,
        match=(
            "Refill completion time cannot "
            "be before start time"
        ),
    ):
        calculate_refill_duration_seconds(
            started_at=started_at,
            completed_at=completed_at,
        )


# ============================================================
# LIFECYCLE
# ============================================================


def test_terminal_refill_requires_completion_time():
    with pytest.raises(
        RefillCalculationError,
        match=(
            "Terminal refill status requires "
            "a completion time"
        ),
    ):
        validate_refill_lifecycle(
            status=ExecutionStatus.COMPLETED,
            completed_at=None,
            timeout_reason=None,
        )


def test_active_refill_cannot_have_completion_time():
    with pytest.raises(
        RefillCalculationError,
        match=(
            "Active refill status cannot "
            "have a completion time"
        ),
    ):
        validate_refill_lifecycle(
            status=ExecutionStatus.RUNNING,
            completed_at=datetime.now(
                timezone.utc
            ),
            timeout_reason=None,
        )


def test_timeout_requires_reason():
    with pytest.raises(
        RefillCalculationError,
        match=(
            "Timed out refill requires "
            "a timeout reason"
        ),
    ):
        validate_refill_lifecycle(
            status=ExecutionStatus.TIMEOUT,
            completed_at=datetime.now(
                timezone.utc
            ),
            timeout_reason=None,
        )


def test_non_timeout_status_rejects_timeout_reason():
    with pytest.raises(
        RefillCalculationError,
        match=(
            "Timeout reason is only valid "
            "for timed out refill events"
        ),
    ):
        validate_refill_lifecycle(
            status=ExecutionStatus.COMPLETED,
            completed_at=datetime.now(
                timezone.utc
            ),
            timeout_reason="Pump timeout",
        )


# ============================================================
# COMPLETE EVENT PLAN
# ============================================================


def test_build_completed_refill_event_plan():
    started_at = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    completed_at = (
        started_at
        + timedelta(seconds=45)
    )

    plan = build_refill_event_plan(
        start_level_percent=30.0,
        end_level_percent=75.0,
        started_at=started_at,
        completed_at=completed_at,
        trigger=RefillTrigger.AUTOMATIC,
        status=ExecutionStatus.COMPLETED,
    )

    assert plan.start_level_percent == pytest.approx(
        30.0
    )

    assert plan.end_level_percent == pytest.approx(
        75.0
    )

    assert plan.level_change_percent == pytest.approx(
        45.0
    )

    assert plan.duration_seconds == pytest.approx(
        45.0
    )

    assert (
        plan.trigger
        == RefillTrigger.AUTOMATIC
    )

    assert (
        plan.status
        == ExecutionStatus.COMPLETED
    )

    assert plan.timeout_reason is None


def test_build_running_refill_event_plan():
    started_at = datetime.now(
        timezone.utc
    )

    plan = build_refill_event_plan(
        start_level_percent=20.0,
        end_level_percent=20.0,
        started_at=started_at,
        completed_at=None,
        trigger=RefillTrigger.MANUAL,
        status=ExecutionStatus.RUNNING,
    )

    assert plan.duration_seconds is None

    assert (
        plan.status
        == ExecutionStatus.RUNNING
    )


def test_build_timeout_refill_event_plan():
    started_at = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    completed_at = (
        started_at
        + timedelta(seconds=120)
    )

    plan = build_refill_event_plan(
        start_level_percent=15.0,
        end_level_percent=35.0,
        started_at=started_at,
        completed_at=completed_at,
        trigger=RefillTrigger.AUTOMATIC,
        status=ExecutionStatus.TIMEOUT,
        timeout_reason="Maximum refill time exceeded",
    )

    assert plan.duration_seconds == pytest.approx(
        120.0
    )

    assert (
        plan.status
        == ExecutionStatus.TIMEOUT
    )

    assert (
        plan.timeout_reason
        == "Maximum refill time exceeded"
    )