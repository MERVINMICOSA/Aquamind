from datetime import datetime, timedelta, timezone

import pytest

from app.db.enums import ExecutionStatus
from app.services.automation_service import (
    AutomationRunPlan,
    AutomationServiceError,
    build_automation_run_plan,
    calculate_automation_run_duration_seconds,
    validate_automation_run_lifecycle,
    validate_automation_trigger_value,
)


# ============================================================
# DURATION
# ============================================================


def test_automation_run_duration_is_calculated():
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

    result = (
        calculate_automation_run_duration_seconds(
            started_at=started_at,
            completed_at=completed_at,
        )
    )

    assert result == pytest.approx(45.0)


def test_active_run_has_no_duration():
    started_at = datetime.now(
        timezone.utc
    )

    result = (
        calculate_automation_run_duration_seconds(
            started_at=started_at,
            completed_at=None,
        )
    )

    assert result is None


def test_completion_before_start_is_rejected():
    started_at = datetime.now(
        timezone.utc
    )

    completed_at = (
        started_at
        - timedelta(seconds=1)
    )

    with pytest.raises(
        AutomationServiceError,
        match=(
            "Automation run completion time "
            "cannot be before start time"
        ),
    ):
        calculate_automation_run_duration_seconds(
            started_at=started_at,
            completed_at=completed_at,
        )


def test_run_start_time_must_be_timezone_aware():
    started_at = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
    )

    with pytest.raises(
        AutomationServiceError,
        match=(
            "Automation run start time "
            "must be timezone-aware"
        ),
    ):
        calculate_automation_run_duration_seconds(
            started_at=started_at,
            completed_at=None,
        )


def test_run_completion_time_must_be_timezone_aware():
    started_at = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    completed_at = datetime(
        2026,
        1,
        1,
        10,
        1,
        0,
    )

    with pytest.raises(
        AutomationServiceError,
        match=(
            "Automation run completion time "
            "must be timezone-aware"
        ),
    ):
        calculate_automation_run_duration_seconds(
            started_at=started_at,
            completed_at=completed_at,
        )


# ============================================================
# ACTIVE LIFECYCLE
# ============================================================


@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.PENDING,
        ExecutionStatus.RUNNING,
    ],
)
def test_active_statuses_allow_no_completion_time(
    status,
):
    started_at = datetime.now(
        timezone.utc
    )

    duration = (
        validate_automation_run_lifecycle(
            status=status,
            started_at=started_at,
            completed_at=None,
        )
    )

    assert duration is None


@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.PENDING,
        ExecutionStatus.RUNNING,
    ],
)
def test_active_statuses_reject_completion_time(
    status,
):
    started_at = datetime.now(
        timezone.utc
    )

    with pytest.raises(
        AutomationServiceError,
        match=(
            "Active automation run cannot "
            "have a completion time"
        ),
    ):
        validate_automation_run_lifecycle(
            status=status,
            started_at=started_at,
            completed_at=(
                started_at
                + timedelta(seconds=10)
            ),
        )


# ============================================================
# TERMINAL LIFECYCLE
# ============================================================


@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.TIMEOUT,
    ],
)
def test_terminal_statuses_require_completion_time(
    status,
):
    started_at = datetime.now(
        timezone.utc
    )

    with pytest.raises(
        AutomationServiceError,
        match=(
            "Terminal automation run requires "
            "a completion time"
        ),
    ):
        validate_automation_run_lifecycle(
            status=status,
            started_at=started_at,
            completed_at=None,
        )


@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.TIMEOUT,
    ],
)
def test_terminal_statuses_accept_completion_time(
    status,
):
    started_at = datetime.now(
        timezone.utc
    )

    completed_at = (
        started_at
        + timedelta(seconds=30)
    )

    duration = (
        validate_automation_run_lifecycle(
            status=status,
            started_at=started_at,
            completed_at=completed_at,
        )
    )

    assert duration == pytest.approx(30.0)


# ============================================================
# TRIGGER VALUE
# ============================================================


def test_trigger_value_can_be_none():
    assert (
        validate_automation_trigger_value(
            None
        )
        is None
    )


def test_trigger_value_is_normalized_to_float():
    result = (
        validate_automation_trigger_value(
            5
        )
    )

    assert result == pytest.approx(5.0)
    assert isinstance(result, float)


def test_non_finite_trigger_value_is_rejected():
    with pytest.raises(
        AutomationServiceError,
        match=(
            "Automation trigger value "
            "must be a finite number"
        ),
    ):
        validate_automation_trigger_value(
            float("nan")
        )


# ============================================================
# COMPLETE RUN PLAN
# ============================================================


def test_build_running_automation_run_plan():
    started_at = datetime.now(
        timezone.utc
    )

    plan = build_automation_run_plan(
        started_at=started_at,
        completed_at=None,
        trigger_value=5.8,
        status=ExecutionStatus.RUNNING,
    )

    assert isinstance(
        plan,
        AutomationRunPlan,
    )

    assert plan.started_at == started_at
    assert plan.completed_at is None

    assert (
        plan.trigger_value
        == pytest.approx(5.8)
    )

    assert (
        plan.status
        == ExecutionStatus.RUNNING
    )

    assert plan.duration_seconds is None
    assert plan.result_summary is None
    assert plan.error_message is None


def test_build_completed_automation_run_plan():
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
        + timedelta(seconds=20)
    )

    plan = build_automation_run_plan(
        started_at=started_at,
        completed_at=completed_at,
        trigger_value=5.8,
        status=ExecutionStatus.COMPLETED,
        result_summary="Pump activated successfully",
    )

    assert (
        plan.status
        == ExecutionStatus.COMPLETED
    )

    assert (
        plan.duration_seconds
        == pytest.approx(20.0)
    )

    assert (
        plan.result_summary
        == "Pump activated successfully"
    )

    assert plan.error_message is None


def test_build_failed_run_can_record_error_message():
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
        + timedelta(seconds=5)
    )

    plan = build_automation_run_plan(
        started_at=started_at,
        completed_at=completed_at,
        trigger_value=5.8,
        status=ExecutionStatus.FAILED,
        error_message="Actuator command failed",
    )

    assert (
        plan.status
        == ExecutionStatus.FAILED
    )

    assert (
        plan.error_message
        == "Actuator command failed"
    )

    assert (
        plan.duration_seconds
        == pytest.approx(5.0)
    )