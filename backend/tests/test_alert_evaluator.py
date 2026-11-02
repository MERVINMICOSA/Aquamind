import pytest

from app.db.enums import AlertSeverity
from app.services.alert_evaluator import evaluate_alert_severity


# ============================================================
# NORMAL RANGE
# ============================================================

def test_value_inside_normal_range_returns_none():
    result = evaluate_alert_severity(
        7.0,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
    )

    assert result is None


# ============================================================
# WARNING LOW
# ============================================================

def test_value_below_warning_low_returns_warning():
    result = evaluate_alert_severity(
        6.3,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
    )

    assert result == AlertSeverity.WARNING


# ============================================================
# WARNING HIGH
# ============================================================

def test_value_above_warning_high_returns_warning():
    result = evaluate_alert_severity(
        7.7,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
    )

    assert result == AlertSeverity.WARNING


# ============================================================
# CRITICAL LOW
# ============================================================

def test_value_at_critical_low_returns_critical():
    result = evaluate_alert_severity(
        6.0,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
    )

    assert result == AlertSeverity.CRITICAL


def test_value_below_critical_low_returns_critical():
    result = evaluate_alert_severity(
        5.5,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
    )

    assert result == AlertSeverity.CRITICAL


# ============================================================
# CRITICAL HIGH
# ============================================================

def test_value_at_critical_high_returns_critical():
    result = evaluate_alert_severity(
        8.0,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
    )

    assert result == AlertSeverity.CRITICAL


def test_value_above_critical_high_returns_critical():
    result = evaluate_alert_severity(
        8.5,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
    )

    assert result == AlertSeverity.CRITICAL


# ============================================================
# WARNING BOUNDARIES
# ============================================================

def test_value_at_warning_low_is_normal():
    result = evaluate_alert_severity(
        6.5,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
    )

    assert result is None


def test_value_at_warning_high_is_normal():
    result = evaluate_alert_severity(
        7.5,
        warning_low=6.5,
        warning_high=7.5,
        critical_low=6.0,
        critical_high=8.0,
    )

    assert result is None


# ============================================================
# OPTIONAL THRESHOLDS
# ============================================================

def test_only_warning_high_can_be_configured():
    result = evaluate_alert_severity(
        8.0,
        warning_high=7.5,
    )

    assert result == AlertSeverity.WARNING


def test_only_critical_low_can_be_configured():
    result = evaluate_alert_severity(
        5.0,
        critical_low=6.0,
    )

    assert result == AlertSeverity.CRITICAL


def test_no_thresholds_returns_none():
    result = evaluate_alert_severity(100.0)

    assert result is None


# ============================================================
# CRITICAL TAKES PRECEDENCE
# ============================================================

def test_critical_takes_precedence_over_warning():
    result = evaluate_alert_severity(
        5.5,
        warning_low=6.5,
        critical_low=6.0,
    )

    assert result == AlertSeverity.CRITICAL


def test_critical_high_takes_precedence_over_warning():
    result = evaluate_alert_severity(
        8.5,
        warning_high=7.5,
        critical_high=8.0,
    )

    assert result == AlertSeverity.CRITICAL