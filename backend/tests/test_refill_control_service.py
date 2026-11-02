from datetime import datetime, timedelta, timezone

import pytest

from app.services.refill_service import (
    RefillCalculationError,
    RefillLevelAction,
    calculate_refill_elapsed_seconds,
    classify_refill_level,
    is_refill_cooldown_active,
    is_refill_timed_out,
    should_stop_refill,
    validate_refill_start_preconditions,
    validate_refill_trigger_thresholds,
)


def test_critical_low_requires_immediate_refill():
    result = classify_refill_level(
        current_level_percent=14.9,
    )

    assert result == RefillLevelAction.IMMEDIATE


def test_exact_critical_boundary_is_scheduled_not_immediate():
    result = classify_refill_level(
        current_level_percent=15.0,
    )

    assert result == RefillLevelAction.SCHEDULED


def test_warning_low_requires_scheduled_refill():
    result = classify_refill_level(
        current_level_percent=24.9,
    )

    assert result == RefillLevelAction.SCHEDULED


def test_exact_warning_boundary_has_no_low_level_trigger():
    result = classify_refill_level(
        current_level_percent=25.0,
    )

    assert result == RefillLevelAction.NONE


def test_invalid_trigger_threshold_order_is_rejected():
    with pytest.raises(
        RefillCalculationError,
        match=(
            "Critical low threshold must be "
            "below warning low threshold"
        ),
    ):
        validate_refill_trigger_thresholds(
            critical_low_percent=25.0,
            warning_low_percent=15.0,
        )


def test_refill_stops_at_target_level():
    assert should_stop_refill(
        current_level_percent=40.0,
    )


def test_refill_continues_below_target_level():
    assert not should_stop_refill(
        current_level_percent=39.9,
    )


def test_refill_elapsed_seconds():
    started_at = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    current_time = (
        started_at
        + timedelta(seconds=125)
    )

    assert calculate_refill_elapsed_seconds(
        started_at=started_at,
        current_time=current_time,
    ) == pytest.approx(125.0)


def test_refill_times_out_at_maximum_duration():
    started_at = datetime.now(
        timezone.utc
    )

    current_time = (
        started_at
        + timedelta(seconds=300)
    )

    assert is_refill_timed_out(
        started_at=started_at,
        current_time=current_time,
    )


def test_refill_does_not_timeout_before_limit():
    started_at = datetime.now(
        timezone.utc
    )

    current_time = (
        started_at
        + timedelta(seconds=299.9)
    )

    assert not is_refill_timed_out(
        started_at=started_at,
        current_time=current_time,
    )


def test_refill_cooldown_is_active_before_thirty_minutes():
    completed_at = datetime.now(
        timezone.utc
    )

    current_time = (
        completed_at
        + timedelta(minutes=29)
    )

    assert is_refill_cooldown_active(
        last_completed_at=completed_at,
        current_time=current_time,
    )


def test_refill_cooldown_expires_at_thirty_minutes():
    completed_at = datetime.now(
        timezone.utc
    )

    current_time = (
        completed_at
        + timedelta(minutes=30)
    )

    assert not is_refill_cooldown_active(
        last_completed_at=completed_at,
        current_time=current_time,
    )


def test_active_refill_blocks_new_refill():
    with pytest.raises(
        RefillCalculationError,
        match="Refill is already active",
    ):
        validate_refill_start_preconditions(
            refill_active=True,
            reservoir_has_water=True,
        )


def test_empty_reservoir_blocks_refill():
    with pytest.raises(
        RefillCalculationError,
        match=(
            "Reservoir does not have enough "
            "water for refill"
        ),
    ):
        validate_refill_start_preconditions(
            refill_active=False,
            reservoir_has_water=False,
        )