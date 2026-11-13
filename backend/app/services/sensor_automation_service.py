from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    AutomationTriggerType,
    CalibrationStatus,
    ReadingQuality,
    SensorType,
)
from app.models.automation import (
    AutomationRule,
)
from app.models.sensors import (
    Sensor,
    SensorReading,
)
from app.services.actuator_executor import (
    ActuatorExecutor,
)
from app.services.automation_runtime_service import (
    AutomationExecutionRequest,
    AutomationRuntimeServiceError,
    create_automation_execution_records,
    execute_and_reconcile_automation_execution,
    prepare_automation_execution_request,
)
from app.services.automation_service import (
    AutomationServiceError,
    prepare_sensor_threshold_automation_decision,
)


# ============================================================
# EXCEPTIONS
# ============================================================


class SensorAutomationServiceError(ValueError):
    """Raised when sensor automation processing is invalid."""


# ============================================================
# RESULT TYPES
# ============================================================


class SensorAutomationOutcome(str, Enum):
    EXECUTED = "executed"
    SKIPPED = "skipped"
    SUPERSEDED = "superseded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SensorAutomationRuleResult:
    rule_id: UUID
    priority: int
    outcome: SensorAutomationOutcome

    actuator_id: UUID | None = None

    automation_run_id: UUID | None = None
    actuator_event_id: UUID | None = None

    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SensorAutomationProcessingResult:
    reading_id: UUID
    sensor_id: UUID

    rule_results: tuple[
        SensorAutomationRuleResult,
        ...
    ]

    @property
    def executed_count(self) -> int:
        return sum(
            result.outcome
            == SensorAutomationOutcome.EXECUTED
            for result in self.rule_results
        )

    @property
    def failed_count(self) -> int:
        return sum(
            result.outcome
            == SensorAutomationOutcome.FAILED
            for result in self.rule_results
        )


# ============================================================
# INTERNAL HELPERS
# ============================================================


def _require_aware_datetime(
    value: datetime,
) -> datetime:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise SensorAutomationServiceError(
            "Automation processing time "
            "must be timezone-aware"
        )

    return value


def _skip_reason(
    decision,
) -> str:
    if not decision.eligibility.eligible:
        return decision.eligibility.reason.value

    if not decision.condition_matched:
        return "condition_not_matched"

    return "not_executable"


# ============================================================
# SENSOR AUTOMATION PROCESSING
# ============================================================


async def process_sensor_reading_automation(
    session: AsyncSession,
    *,
    reading: SensorReading,
    executor: ActuatorExecutor,
    current_time: datetime | None = None,
) -> SensorAutomationProcessingResult:
    """
    Process one already-persisted sensor reading through the
    automation runtime.

    Important runtime rules:

    - only GOOD readings can trigger automation;
    - only enabled SENSOR_THRESHOLD rules from the same system
      are considered;
    - higher numeric priority executes first;
    - one sensor reading can issue at most one command to the
      same actuator;
    - different actuators may execute independently;
    - one malformed/runtime-invalid rule does not block another
      valid rule;
    - infrastructure/database errors are intentionally not
      swallowed.
    """

    evaluation_time = _require_aware_datetime(
        current_time
        or datetime.now(timezone.utc)
    )

    # --------------------------------------------------------
    # Reading quality
    # --------------------------------------------------------

    if (
        reading.quality_status
        != ReadingQuality.GOOD
    ):
        return SensorAutomationProcessingResult(
            reading_id=reading.id,
            sensor_id=reading.sensor_id,
            rule_results=(),
        )

    # --------------------------------------------------------
    # Owning sensor
    # --------------------------------------------------------

    sensor = await session.get(
        Sensor,
        reading.sensor_id,
    )

    if (
        sensor is None
        or sensor.deleted_at is not None
        or not sensor.is_enabled
    ):
        return SensorAutomationProcessingResult(
            reading_id=reading.id,
            sensor_id=reading.sensor_id,
            rule_results=(),
        )

    # Never issue control commands based on pH/TDS readings whose
    # registered sensor is pending, rejected, or calibration-expired.
    # This complements the alert gate and does not constitute physical
    # proof of probe calibration.
    if (
        sensor.sensor_type in (SensorType.PH, SensorType.TDS)
        and sensor.calibration_status != CalibrationStatus.VERIFIED
    ):
        return SensorAutomationProcessingResult(
            reading_id=reading.id,
            sensor_id=reading.sensor_id,
            rule_results=(),
        )

    # --------------------------------------------------------
    # Candidate rules
    #
    # Existing AquaMind convention:
    # higher numeric priority comes first.
    #
    # created_at + id provide deterministic ordering when
    # priorities are equal.
    # --------------------------------------------------------

    rule_result = await session.execute(
        select(AutomationRule)
        .where(
            AutomationRule.system_id
            == sensor.system_id,
            AutomationRule.trigger_type
            == AutomationTriggerType.SENSOR_THRESHOLD,
            AutomationRule.enabled.is_(True),
        )
        .order_by(
            AutomationRule.priority.desc(),
            AutomationRule.created_at.asc(),
            AutomationRule.id.asc(),
        )
    )

    rules = list(
        rule_result.scalars().all()
    )

    ordered_rule_ids = [
        rule.id
        for rule in rules
    ]

    results_by_rule: dict[
        UUID,
        SensorAutomationRuleResult,
    ] = {}

    candidates: list[
        tuple[
            UUID,
            int,
            AutomationExecutionRequest,
        ]
    ] = []

    # --------------------------------------------------------
    # Phase 6 decision evaluation + 8A request preparation
    # --------------------------------------------------------

    for rule in rules:
        rule_id = rule.id
        priority = rule.priority

        try:
            decision = (
                await prepare_sensor_threshold_automation_decision(
                    session,
                    rule_id=rule_id,
                    sensor_type=(
                        sensor.sensor_type.value
                    ),
                    measurement_type=(
                        sensor.measurement_type.value
                    ),
                    trigger_value=float(
                        reading.value_numeric
                    ),
                    current_time=evaluation_time,
                )
            )

            if not decision.should_execute:
                results_by_rule[
                    rule_id
                ] = SensorAutomationRuleResult(
                    rule_id=rule_id,
                    priority=priority,
                    outcome=(
                        SensorAutomationOutcome.SKIPPED
                    ),
                    reason=_skip_reason(
                        decision
                    ),
                )

                continue

            request = (
                await prepare_automation_execution_request(
                    session,
                    decision=decision,
                )
            )

            candidates.append(
                (
                    rule_id,
                    priority,
                    request,
                )
            )

        except (
            AutomationServiceError,
            AutomationRuntimeServiceError,
        ) as exc:
            # These are rule/configuration/runtime-boundary
            # failures. Isolate the rule and continue.
            results_by_rule[
                rule_id
            ] = SensorAutomationRuleResult(
                rule_id=rule_id,
                priority=priority,
                outcome=(
                    SensorAutomationOutcome.FAILED
                ),
                reason=(
                    str(exc).strip()
                    or "Automation rule processing failed"
                ),
            )

    # --------------------------------------------------------
    # Per-actuator arbitration
    #
    # candidates already follow descending priority.
    # Therefore the first request for an actuator wins.
    #
    # This prevents one reading from issuing redundant or
    # conflicting commands to the same physical actuator.
    # --------------------------------------------------------

    selected_actuator_ids: set[
        UUID
    ] = set()

    selected: list[
        tuple[
            UUID,
            int,
            AutomationExecutionRequest,
        ]
    ] = []

    for (
        rule_id,
        priority,
        request,
    ) in candidates:
        if (
            request.actuator_id
            in selected_actuator_ids
        ):
            results_by_rule[
                rule_id
            ] = SensorAutomationRuleResult(
                rule_id=rule_id,
                priority=priority,
                outcome=(
                    SensorAutomationOutcome.SUPERSEDED
                ),
                actuator_id=(
                    request.actuator_id
                ),
                reason=(
                    "higher_priority_rule_selected_"
                    "for_same_actuator"
                ),
            )

            continue

        selected_actuator_ids.add(
            request.actuator_id
        )

        selected.append(
            (
                rule_id,
                priority,
                request,
            )
        )

    # --------------------------------------------------------
    # 8B → 8C → 8D execution
    #
    # Execute sequentially on one AsyncSession.
    # AsyncSession must not be used concurrently.
    # --------------------------------------------------------

    for (
        rule_id,
        priority,
        request,
    ) in selected:
        records = None

        try:
            records = (
                await create_automation_execution_records(
                    session,
                    request=request,
                    started_at=evaluation_time,
                )
            )

            records = (
                await execute_and_reconcile_automation_execution(
                    session,
                    request=request,
                    records=records,
                    executor=executor,
                )
            )

            results_by_rule[
                rule_id
            ] = SensorAutomationRuleResult(
                rule_id=rule_id,
                priority=priority,
                outcome=(
                    SensorAutomationOutcome.EXECUTED
                ),
                actuator_id=(
                    request.actuator_id
                ),
                automation_run_id=(
                    records.automation_run.id
                ),
                actuator_event_id=(
                    records.actuator_event.id
                ),
            )

        except AutomationRuntimeServiceError as exc:
            # Runtime services already persist a FAILED outcome
            # when execution itself fails. Rollback here only
            # clears any remaining transaction state before the
            # next independent rule is processed.
            await session.rollback()

            results_by_rule[
                rule_id
            ] = SensorAutomationRuleResult(
                rule_id=rule_id,
                priority=priority,
                outcome=(
                    SensorAutomationOutcome.FAILED
                ),
                actuator_id=(
                    request.actuator_id
                ),
                automation_run_id=(
                    records.automation_run.id
                    if records is not None
                    else None
                ),
                actuator_event_id=(
                    records.actuator_event.id
                    if records is not None
                    else None
                ),
                reason=(
                    str(exc).strip()
                    or "Automation execution failed"
                ),
            )

    # --------------------------------------------------------
    # Preserve deterministic priority order in returned report
    # --------------------------------------------------------

    ordered_results = tuple(
        results_by_rule[rule_id]
        for rule_id in ordered_rule_ids
        if rule_id in results_by_rule
    )

    return SensorAutomationProcessingResult(
        reading_id=reading.id,
        sensor_id=sensor.id,
        rule_results=ordered_results,
    )