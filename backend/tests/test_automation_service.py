import pytest

from app.services.automation_service import (
    AutomationServiceError,
    SensorThresholdCondition,
    evaluate_sensor_threshold_condition,
    parse_sensor_threshold_condition,
)


# ============================================================
# CONDITION PARSING
# ============================================================


def test_parse_sensor_threshold_condition():
    condition = (
        parse_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "less_than",
                "value": 6.0,
            }
        )
    )

    assert isinstance(
        condition,
        SensorThresholdCondition,
    )

    assert condition.sensor_type == "ph"
    assert condition.measurement_type == "ph"
    assert condition.operator == "less_than"

    assert (
        condition.threshold_value
        == pytest.approx(6.0)
    )


def test_parse_condition_strips_string_values():
    condition = (
        parse_sensor_threshold_condition(
            {
                "sensor_type": " ph ",
                "measurement_type": " ph ",
                "operator": " less_than ",
                "value": 6.0,
            }
        )
    )

    assert condition.sensor_type == "ph"
    assert condition.measurement_type == "ph"
    assert condition.operator == "less_than"


def test_condition_requires_sensor_type():
    with pytest.raises(
        AutomationServiceError,
        match="sensor_type must be a string",
    ):
        parse_sensor_threshold_condition(
            {
                "measurement_type": "ph",
                "operator": "less_than",
                "value": 6.0,
            }
        )


def test_condition_requires_measurement_type():
    with pytest.raises(
        AutomationServiceError,
        match=(
            "measurement_type must be a string"
        ),
    ):
        parse_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "operator": "less_than",
                "value": 6.0,
            }
        )


def test_condition_rejects_unknown_operator():
    with pytest.raises(
        AutomationServiceError,
        match=(
            "Unsupported sensor threshold operator"
        ),
    ):
        parse_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "between",
                "value": 6.0,
            }
        )


def test_condition_requires_threshold_value():
    with pytest.raises(
        AutomationServiceError,
        match=(
            "Sensor threshold condition "
            "requires value"
        ),
    ):
        parse_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "less_than",
            }
        )


def test_condition_rejects_non_finite_threshold():
    with pytest.raises(
        AutomationServiceError,
        match=(
            "Threshold value must be "
            "a finite number"
        ),
    ):
        parse_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "less_than",
                "value": float("nan"),
            }
        )


# ============================================================
# LESS-THAN EVALUATION
# ============================================================


def test_less_than_condition_matches():
    result = (
        evaluate_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "less_than",
                "value": 6.0,
            },
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=5.8,
        )
    )

    assert result is True


def test_less_than_condition_does_not_match_boundary():
    result = (
        evaluate_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "less_than",
                "value": 6.0,
            },
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=6.0,
        )
    )

    assert result is False


# ============================================================
# GREATER-THAN EVALUATION
# ============================================================


def test_greater_than_condition_matches():
    result = (
        evaluate_sensor_threshold_condition(
            {
                "sensor_type": "water_temp",
                "measurement_type": (
                    "water_temperature"
                ),
                "operator": "greater_than",
                "value": 28.0,
            },
            sensor_type="water_temp",
            measurement_type=(
                "water_temperature"
            ),
            trigger_value=29.5,
        )
    )

    assert result is True


def test_greater_than_condition_does_not_match_boundary():
    result = (
        evaluate_sensor_threshold_condition(
            {
                "sensor_type": "water_temp",
                "measurement_type": (
                    "water_temperature"
                ),
                "operator": "greater_than",
                "value": 28.0,
            },
            sensor_type="water_temp",
            measurement_type=(
                "water_temperature"
            ),
            trigger_value=28.0,
        )
    )

    assert result is False


# ============================================================
# SOURCE MATCHING
# ============================================================


def test_different_sensor_does_not_match_rule():
    result = (
        evaluate_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "less_than",
                "value": 6.0,
            },
            sensor_type="tds",
            measurement_type="ph",
            trigger_value=5.5,
        )
    )

    assert result is False


def test_different_measurement_does_not_match_rule():
    result = (
        evaluate_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "less_than",
                "value": 6.0,
            },
            sensor_type="ph",
            measurement_type="temperature",
            trigger_value=5.5,
        )
    )

    assert result is False


def test_trigger_value_must_be_finite():
    with pytest.raises(
        AutomationServiceError,
        match=(
            "Trigger value must be "
            "a finite number"
        ),
    ):
        evaluate_sensor_threshold_condition(
            {
                "sensor_type": "ph",
                "measurement_type": "ph",
                "operator": "less_than",
                "value": 6.0,
            },
            sensor_type="ph",
            measurement_type="ph",
            trigger_value=float("inf"),
        )