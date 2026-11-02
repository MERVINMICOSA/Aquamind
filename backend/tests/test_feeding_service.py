import pytest

from app.services.feeding_service import (
    FeedingCalculationError,
    build_feeding_plan,
    calculate_feed_amount_per_feeding,
    calculate_feed_duration_seconds,
    calculate_grams_per_second,
)


def test_calculate_grams_per_second_from_measurements():
    result = calculate_grams_per_second(
        measured_grams=50.0,
        measured_seconds=10.0,
    )

    assert result == pytest.approx(5.0)


def test_calibration_rejects_zero_measured_seconds():
    with pytest.raises(
        FeedingCalculationError,
        match="Measured seconds must be greater than zero",
    ):
        calculate_grams_per_second(
            measured_grams=50.0,
            measured_seconds=0.0,
        )


def test_calibration_rejects_nonpositive_measured_grams():
    with pytest.raises(
        FeedingCalculationError,
        match="Measured grams must be greater than zero",
    ):
        calculate_grams_per_second(
            measured_grams=0.0,
            measured_seconds=10.0,
        )


def test_feed_amount_uses_biomass_rate_and_feeding_count():
    result = calculate_feed_amount_per_feeding(
        biomass_grams=25000.0,
        daily_feed_rate_percent=1.0,
        feeds_per_day=5,
        max_per_feed_grams=100.0,
    )

    # 25,000 g biomass
    # × 1% = 250 g/day
    # ÷ 5 feeds = 50 g/feed
    assert result == pytest.approx(50.0)


def test_feed_amount_is_capped_by_schedule_limit():
    result = calculate_feed_amount_per_feeding(
        biomass_grams=25000.0,
        daily_feed_rate_percent=2.0,
        feeds_per_day=4,
        max_per_feed_grams=100.0,
    )

    # 25,000 × 2% = 500 g/day
    # 500 / 4 = 125 g/feed
    # schedule cap = 100 g
    assert result == pytest.approx(100.0)


def test_zero_biomass_returns_zero_feed():
    result = calculate_feed_amount_per_feeding(
        biomass_grams=0.0,
        daily_feed_rate_percent=2.0,
        feeds_per_day=4,
        max_per_feed_grams=100.0,
    )

    assert result == 0.0


def test_feed_amount_rejects_invalid_inputs():
    with pytest.raises(
        FeedingCalculationError,
        match="Biomass cannot be negative",
    ):
        calculate_feed_amount_per_feeding(
            biomass_grams=-1.0,
            daily_feed_rate_percent=2.0,
            feeds_per_day=4,
            max_per_feed_grams=100.0,
        )

    with pytest.raises(
        FeedingCalculationError,
        match="Daily feed rate percent must be greater than zero",
    ):
        calculate_feed_amount_per_feeding(
            biomass_grams=25000.0,
            daily_feed_rate_percent=0.0,
            feeds_per_day=4,
            max_per_feed_grams=100.0,
        )

    with pytest.raises(
        FeedingCalculationError,
        match="Feeds per day must be greater than zero",
    ):
        calculate_feed_amount_per_feeding(
            biomass_grams=25000.0,
            daily_feed_rate_percent=2.0,
            feeds_per_day=0,
            max_per_feed_grams=100.0,
        )

    with pytest.raises(
        FeedingCalculationError,
        match="Maximum feed amount must be greater than zero",
    ):
        calculate_feed_amount_per_feeding(
            biomass_grams=25000.0,
            daily_feed_rate_percent=2.0,
            feeds_per_day=4,
            max_per_feed_grams=0.0,
        )


def test_duration_is_amount_divided_by_calibration_rate():
    result = calculate_feed_duration_seconds(
        amount_grams=50.0,
        grams_per_second=5.0,
    )

    assert result == pytest.approx(10.0)


def test_zero_feed_amount_has_zero_duration():
    result = calculate_feed_duration_seconds(
        amount_grams=0.0,
        grams_per_second=5.0,
    )

    assert result == 0.0


def test_duration_rejects_invalid_calibration_rate():
    with pytest.raises(
        FeedingCalculationError,
        match="Feeder calibration rate must be greater than zero",
    ):
        calculate_feed_duration_seconds(
            amount_grams=50.0,
            grams_per_second=0.0,
        )


def test_build_feeding_plan_returns_expected_values():
    plan = build_feeding_plan(
        biomass_grams=25000.0,
        daily_feed_rate_percent=1.0,
        feeds_per_day=5,
        max_per_feed_grams=100.0,
        measured_grams=50.0,
        measured_seconds=10.0,
        max_runtime_seconds=30.0,
    )

    assert plan.biomass_grams == pytest.approx(
        25000.0
    )

    assert plan.daily_feed_grams == pytest.approx(
        250.0
    )

    assert plan.uncapped_amount_grams == pytest.approx(
        50.0
    )

    assert plan.amount_grams == pytest.approx(
        50.0
    )

    assert plan.capped_by_schedule is False

    assert plan.grams_per_second == pytest.approx(
        5.0
    )

    assert plan.duration_seconds == pytest.approx(
        10.0
    )


def test_build_feeding_plan_reports_schedule_cap():
    plan = build_feeding_plan(
        biomass_grams=25000.0,
        daily_feed_rate_percent=2.0,
        feeds_per_day=4,
        max_per_feed_grams=100.0,
        measured_grams=50.0,
        measured_seconds=10.0,
    )

    assert plan.daily_feed_grams == pytest.approx(
        500.0
    )

    assert plan.uncapped_amount_grams == pytest.approx(
        125.0
    )

    assert plan.amount_grams == pytest.approx(
        100.0
    )

    assert plan.capped_by_schedule is True

    assert plan.duration_seconds == pytest.approx(
        20.0
    )


def test_build_feeding_plan_rejects_runtime_over_safety_limit():
    with pytest.raises(
        FeedingCalculationError,
        match=(
            "Calculated feeder runtime exceeds "
            "actuator safety limit"
        ),
    ):
        build_feeding_plan(
            biomass_grams=25000.0,
            daily_feed_rate_percent=2.0,
            feeds_per_day=4,
            max_per_feed_grams=100.0,
            measured_grams=20.0,
            measured_seconds=10.0,
            max_runtime_seconds=30.0,
        )