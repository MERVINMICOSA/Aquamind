from __future__ import annotations

from app.db.enums import AlertSeverity


def evaluate_alert_severity(
    value: float,
    *,
    warning_low: float | None = None,
    warning_high: float | None = None,
    critical_low: float | None = None,
    critical_high: float | None = None,
) -> AlertSeverity | None:
    """
    Evaluate a numeric sensor value against alert thresholds.

    Returns:

    - AlertSeverity.CRITICAL when a critical threshold is violated.
    - AlertSeverity.WARNING when a warning threshold is violated.
    - None when the value is within the normal range.

    Critical thresholds take precedence over warning thresholds.
    """

    # ------------------------------------------------------------
    # CRITICAL LOW
    # ------------------------------------------------------------

    if critical_low is not None and value <= critical_low:
        return AlertSeverity.CRITICAL

    # ------------------------------------------------------------
    # CRITICAL HIGH
    # ------------------------------------------------------------

    if critical_high is not None and value >= critical_high:
        return AlertSeverity.CRITICAL

    # ------------------------------------------------------------
    # WARNING LOW
    # ------------------------------------------------------------

    if warning_low is not None and value < warning_low:
        return AlertSeverity.WARNING

    # ------------------------------------------------------------
    # WARNING HIGH
    # ------------------------------------------------------------

    if warning_high is not None and value > warning_high:
        return AlertSeverity.WARNING

    # ------------------------------------------------------------
    # NORMAL
    # ------------------------------------------------------------

    return None