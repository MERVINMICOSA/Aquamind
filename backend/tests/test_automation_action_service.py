import pytest

from app.services.automation_service import (
    AutomationServiceError,
    PreparedAutomationAction,
    parse_automation_action_definition,
)


# ============================================================
# VALID ACTION
# ============================================================


def test_parse_activate_actuator_action():
    action = parse_automation_action_definition(
        {
            "action": "activate_actuator",
            "actuator_type": "water_pump",
            "value": 1.0,
        }
    )

    assert isinstance(
        action,
        PreparedAutomationAction,
    )

    assert action.action == "activate_actuator"

    assert (
        action.actuator_type
        == "water_pump"
    )

    assert action.value == pytest.approx(
        1.0
    )


def test_action_definition_strips_string_values():
    action = parse_automation_action_definition(
        {
            "action": " activate_actuator ",
            "actuator_type": " water_pump ",
            "value": 1.0,
        }
    )

    assert action.action == "activate_actuator"

    assert (
        action.actuator_type
        == "water_pump"
    )


def test_integer_action_value_is_normalized_to_float():
    action = parse_automation_action_definition(
        {
            "action": "activate_actuator",
            "actuator_type": "water_pump",
            "value": 1,
        }
    )

    assert action.value == pytest.approx(
        1.0
    )

    assert isinstance(
        action.value,
        float,
    )


# ============================================================
# ACTION VALIDATION
# ============================================================


def test_action_definition_must_be_object():
    with pytest.raises(
        AutomationServiceError,
        match=(
            "Automation action definition "
            "must be an object"
        ),
    ):
        parse_automation_action_definition(
            None
        )


def test_action_name_is_required():
    with pytest.raises(
        AutomationServiceError,
        match="action must be a string",
    ):
        parse_automation_action_definition(
            {
                "actuator_type": "water_pump",
                "value": 1.0,
            }
        )


def test_empty_action_name_is_rejected():
    with pytest.raises(
        AutomationServiceError,
        match="action cannot be empty",
    ):
        parse_automation_action_definition(
            {
                "action": "   ",
                "actuator_type": "water_pump",
                "value": 1.0,
            }
        )


def test_unsupported_action_is_rejected():
    with pytest.raises(
        AutomationServiceError,
        match="Unsupported automation action",
    ):
        parse_automation_action_definition(
            {
                "action": "delete_system",
                "actuator_type": "water_pump",
                "value": 1.0,
            }
        )


def test_actuator_type_is_required():
    with pytest.raises(
        AutomationServiceError,
        match="actuator_type must be a string",
    ):
        parse_automation_action_definition(
            {
                "action": "activate_actuator",
                "value": 1.0,
            }
        )


def test_empty_actuator_type_is_rejected():
    with pytest.raises(
        AutomationServiceError,
        match="actuator_type cannot be empty",
    ):
        parse_automation_action_definition(
            {
                "action": "activate_actuator",
                "actuator_type": "   ",
                "value": 1.0,
            }
        )


def test_action_value_is_required():
    with pytest.raises(
        AutomationServiceError,
        match="Automation action requires value",
    ):
        parse_automation_action_definition(
            {
                "action": "activate_actuator",
                "actuator_type": "water_pump",
            }
        )


def test_non_numeric_action_value_is_rejected():
    with pytest.raises(
        AutomationServiceError,
        match=(
            "Automation action value "
            "must be a number"
        ),
    ):
        parse_automation_action_definition(
            {
                "action": "activate_actuator",
                "actuator_type": "water_pump",
                "value": "on",
            }
        )


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_non_finite_action_value_is_rejected(
    value,
):
    with pytest.raises(
        AutomationServiceError,
        match=(
            "Automation action value "
            "must be a finite number"
        ),
    ):
        parse_automation_action_definition(
            {
                "action": "activate_actuator",
                "actuator_type": "water_pump",
                "value": value,
            }
        )