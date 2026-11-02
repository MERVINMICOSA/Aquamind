from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    ActuatorCommandType,
    ActuatorState,
    ActuatorType,
    ControlMode,
    ExecutionStatus,
    TriggerSource,
)
from app.models.actuators import (
    Actuator,
    ActuatorEvent,
)
from app.models.automation import (
    AutomationRule,
    AutomationRun,
)
from app.services.automation_service import (
    AutomationServiceError,
    PreparedAutomationDecision,
    TERMINAL_AUTOMATION_STATUSES,
    build_automation_run_plan,
    evaluate_automation_rule_eligibility,
)
from app.services.actuator_executor import (
    ActuatorExecutionCommand,
    ActuatorExecutionResult,
    ActuatorExecutor,
)


# ============================================================
# EXCEPTIONS
# ============================================================


class AutomationRuntimeServiceError(ValueError):
    """Raised when an automation decision cannot be dispatched."""


# ============================================================
# DATA OBJECTS
# ============================================================


@dataclass(frozen=True, slots=True)
class AutomationExecutionRequest:
    rule_id: UUID
    system_id: UUID

    actuator_id: UUID
    actuator_type: ActuatorType

    command_type: ActuatorCommandType
    requested_value: float

    trigger_source: TriggerSource
    trigger_value: float

    priority: int


@dataclass(frozen=True, slots=True)
class AutomationExecutionRecords:
    automation_run: AutomationRun
    actuator_event: ActuatorEvent


# ============================================================
# ACTION MAPPING
# ============================================================


AUTOMATION_COMMAND_MAP = {
    "activate_actuator": (
        ActuatorCommandType.ACTIVATE
    ),
}


def _resolve_actuator_type(
    value: str,
) -> ActuatorType:
    try:
        return ActuatorType(value)
    except ValueError as exc:
        raise AutomationRuntimeServiceError(
            "Unsupported automation actuator type"
        ) from exc


def _resolve_command_type(
    action: str,
) -> ActuatorCommandType:
    command_type = (
        AUTOMATION_COMMAND_MAP.get(
            action
        )
    )

    if command_type is None:
        raise AutomationRuntimeServiceError(
            "Unsupported automation runtime action"
        )

    return command_type


# ============================================================
# ACTUATOR RESOLUTION
# ============================================================


async def _resolve_automation_actuator(
    session: AsyncSession,
    *,
    system_id: UUID,
    actuator_type: ActuatorType,
) -> Actuator:
    result = await session.execute(
        select(Actuator).where(
            Actuator.system_id
            == system_id,
            Actuator.actuator_type
            == actuator_type,
            Actuator.control_mode
            == ControlMode.AUTOMATIC,
            Actuator.is_enabled.is_(True),
            Actuator.deleted_at.is_(None),
        )
    )

    actuators = list(
        result.scalars().all()
    )

    if not actuators:
        raise AutomationRuntimeServiceError(
            "No eligible actuator found for automation action"
        )

    if len(actuators) > 1:
        raise AutomationRuntimeServiceError(
            "Automation actuator target is ambiguous"
        )

    return actuators[0]


# ============================================================
# EXECUTION REQUEST PREPARATION
# ============================================================


async def prepare_automation_execution_request(
    session: AsyncSession,
    *,
    decision: PreparedAutomationDecision,
) -> AutomationExecutionRequest:
    # Phase 6 owns whether the rule is eligible and whether its
    # trigger condition matched. Phase 8 consumes that decision
    # without reimplementing the business rules.
    if (
        not decision.should_execute
        or not decision.condition_matched
        or decision.action is None
    ):
        raise AutomationRuntimeServiceError(
            "Automation decision is not executable"
        )

    rule = await session.get(
        AutomationRule,
        decision.rule_id,
    )

    if rule is None:
        raise AutomationRuntimeServiceError(
            "Automation rule not found"
        )

    actuator_type = _resolve_actuator_type(
        decision.action.actuator_type
    )

    command_type = _resolve_command_type(
        decision.action.action
    )

    actuator = (
        await _resolve_automation_actuator(
            session,
            system_id=rule.system_id,
            actuator_type=actuator_type,
        )
    )

    return AutomationExecutionRequest(
        rule_id=rule.id,
        system_id=rule.system_id,
        actuator_id=actuator.id,
        actuator_type=actuator.actuator_type,
        command_type=command_type,
        requested_value=(
            decision.action.value
        ),
        trigger_source=(
            TriggerSource.AUTOMATION
        ),
        trigger_value=(
            decision.trigger_value
        ),
        priority=decision.priority,
    )


# ============================================================
# EXECUTION REQUEST REVALIDATION
# ============================================================


async def _validate_execution_request(
    session: AsyncSession,
    *,
    request: AutomationExecutionRequest,
    lock_rule: bool = False,
    lock_actuator: bool = False,
) -> tuple[AutomationRule, Actuator]:
    if (
        request.trigger_source
        != TriggerSource.AUTOMATION
    ):
        raise AutomationRuntimeServiceError(
            "Automation execution request must use "
            "automation trigger source"
        )

    # --------------------------------------------------------
    # RULE
    # --------------------------------------------------------

    if lock_rule:
        result = await session.execute(
            select(AutomationRule)
            .where(
                AutomationRule.id
                == request.rule_id
            )
            .with_for_update()
        )

        rule = (
            result.scalar_one_or_none()
        )

    else:
        rule = await session.get(
            AutomationRule,
            request.rule_id,
        )

    if rule is None:
        raise AutomationRuntimeServiceError(
            "Automation rule not found"
        )

    if rule.system_id != request.system_id:
        raise AutomationRuntimeServiceError(
            "Automation execution request system "
            "does not match rule"
        )

    # --------------------------------------------------------
    # ACTUATOR
    # --------------------------------------------------------

    if lock_actuator:
        actuator_result = await session.execute(
            select(Actuator)
            .where(
                Actuator.id
                == request.actuator_id
            )
            .with_for_update()
        )

        actuator = (
            actuator_result.scalar_one_or_none()
        )

    else:
        actuator = await session.get(
            Actuator,
            request.actuator_id,
        )

    if actuator is None:
        raise AutomationRuntimeServiceError(
            "Automation actuator not found"
        )

    if (
        actuator.system_id
        != request.system_id
    ):
        raise AutomationRuntimeServiceError(
            "Automation actuator does not belong "
            "to request system"
        )

    if (
        actuator.actuator_type
        != request.actuator_type
    ):
        raise AutomationRuntimeServiceError(
            "Automation actuator type does not "
            "match request"
        )

    if (
        actuator.deleted_at is not None
        or not actuator.is_enabled
        or actuator.control_mode
        != ControlMode.AUTOMATIC
    ):
        raise AutomationRuntimeServiceError(
            "Automation actuator is no longer eligible"
        )

    return rule, actuator

# ============================================================
# EXECUTION RECORD PREPARATION
# ============================================================


async def create_automation_execution_records(
    session: AsyncSession,
    *,
    request: AutomationExecutionRequest,
    started_at: datetime | None = None,
) -> AutomationExecutionRecords:
    execution_time = (
        started_at
        or datetime.now(timezone.utc)
    )

    # --------------------------------------------------------
    # VALIDATE START TIME
    # --------------------------------------------------------

    try:
        run_plan = build_automation_run_plan(
            started_at=execution_time,
            completed_at=None,
            trigger_value=(
                request.trigger_value
            ),
            status=ExecutionStatus.PENDING,
        )
    except AutomationServiceError as exc:
        raise AutomationRuntimeServiceError(
            "Automation execution start time is invalid"
        ) from exc

    # --------------------------------------------------------
    # RULE EXECUTION CLAIM
    #
    # Serialize competing executions of the same rule first.
    # --------------------------------------------------------

    await _validate_execution_request(
        session,
        request=request,
        lock_rule=True,
        lock_actuator=False,
    )

    # --------------------------------------------------------
    # STALE-DECISION REVALIDATION
    #
    # The original Phase 6 decision may no longer be valid.
    # --------------------------------------------------------

    try:
        eligibility = (
            await evaluate_automation_rule_eligibility(
                session,
                rule_id=request.rule_id,
                current_time=execution_time,
            )
        )

    except AutomationServiceError as exc:
        raise AutomationRuntimeServiceError(
            "Automation rule eligibility "
            "could not be revalidated"
        ) from exc

    if not eligibility.eligible:
        raise AutomationRuntimeServiceError(
            "Automation rule is no longer eligible: "
            f"{eligibility.reason.value}"
        )

    # --------------------------------------------------------
    # ACTUATOR EXECUTION CLAIM
    #
    # The rule is still eligible. Now lock and revalidate the
    # physical actuator.
    # --------------------------------------------------------

    _, actuator = (
        await _validate_execution_request(
            session,
            request=request,
            lock_rule=False,
            lock_actuator=True,
        )
    )

    # --------------------------------------------------------
    # EXISTING ACTIVE ACTUATOR EVENT
    #
    # This MUST happen after the actuator has been locked and
    # before the new ActuatorEvent is constructed or added.
    # --------------------------------------------------------

    active_event_result = await session.execute(
        select(ActuatorEvent)
        .where(
            ActuatorEvent.actuator_id
            == actuator.id,
            ActuatorEvent.status.in_(
                (
                    ExecutionStatus.PENDING,
                    ExecutionStatus.RUNNING,
                )
            ),
        )
        .order_by(
            ActuatorEvent.started_at.desc()
        )
        .limit(1)
    )

    active_event = (
        active_event_result
        .scalars()
        .first()
    )

    if active_event is not None:
        raise AutomationRuntimeServiceError(
            "Automation actuator already has active execution"
        )

    # --------------------------------------------------------
    # CREATE RECORDS
    #
    # Only now, after both execution claims succeeded.
    # --------------------------------------------------------

    automation_run = AutomationRun(
        rule_id=request.rule_id,
        started_at=run_plan.started_at,
        completed_at=run_plan.completed_at,
        trigger_value=run_plan.trigger_value,
        status=run_plan.status,
        result_summary=(
            run_plan.result_summary
        ),
        error_message=(
            run_plan.error_message
        ),
    )

    actuator_event = ActuatorEvent(
        actuator_id=actuator.id,
        command_type=(
            request.command_type
        ),
        requested_value=(
            request.requested_value
        ),
        actual_value=None,
        started_at=execution_time,
        completed_at=None,
        duration_ms=None,
        trigger_source=(
            request.trigger_source
        ),
        status=ExecutionStatus.PENDING,
        fault_code=None,
        error_message=None,
    )

    session.add_all(
        [
            automation_run,
            actuator_event,
        ]
    )

    # --------------------------------------------------------
    # COMMIT CLAIM
    #
    # PostgreSQL releases the row locks after this commit.
    # A waiting transaction then sees this PENDING event and
    # fails its actuator claim safely.
    # --------------------------------------------------------

    await session.commit()

    await session.refresh(
        automation_run
    )

    await session.refresh(
        actuator_event
    )

    return AutomationExecutionRecords(
        automation_run=automation_run,
        actuator_event=actuator_event,
    )


# ============================================================
# EXECUTION LIFECYCLE
# ============================================================


def _normalize_database_datetime(
    value: datetime,
) -> datetime:
    # SQLite test environments may return persisted TIMESTAMPTZ
    # values without tzinfo. The stored value represents UTC.
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value


def _validate_execution_record_pair(
    *,
    request: AutomationExecutionRequest,
    records: AutomationExecutionRecords,
) -> None:
    run = records.automation_run
    event = records.actuator_event

    if run.rule_id != request.rule_id:
        raise AutomationRuntimeServiceError(
            "Automation run does not match execution request"
        )

    if event.actuator_id != request.actuator_id:
        raise AutomationRuntimeServiceError(
            "Actuator event does not match execution request"
        )

    if event.command_type != request.command_type:
        raise AutomationRuntimeServiceError(
            "Actuator event command does not match execution request"
        )

    if (
        event.trigger_source
        != TriggerSource.AUTOMATION
    ):
        raise AutomationRuntimeServiceError(
            "Actuator event trigger source must be automation"
        )

    if (
        run.status
        != ExecutionStatus.PENDING
        or event.status
        != ExecutionStatus.PENDING
    ):
        raise AutomationRuntimeServiceError(
            "Automation execution records are not pending"
        )


async def _mark_execution_running(
    session: AsyncSession,
    *,
    records: AutomationExecutionRecords,
) -> None:
    run = records.automation_run
    event = records.actuator_event

    started_at = _normalize_database_datetime(
        run.started_at
    )

    try:
        build_automation_run_plan(
            started_at=started_at,
            completed_at=None,
            trigger_value=run.trigger_value,
            status=ExecutionStatus.RUNNING,
        )
    except AutomationServiceError as exc:
        raise AutomationRuntimeServiceError(
            "Automation execution cannot enter running state"
        ) from exc

    run.status = ExecutionStatus.RUNNING
    event.status = ExecutionStatus.RUNNING

    await session.commit()

    await session.refresh(run)
    await session.refresh(event)


async def _finalize_execution(
    session: AsyncSession,
    *,
    records: AutomationExecutionRecords,
    result: ActuatorExecutionResult,
) -> AutomationExecutionRecords:
    run = records.automation_run
    event = records.actuator_event

    if (
        result.status
        not in TERMINAL_AUTOMATION_STATUSES
    ):
        raise AutomationRuntimeServiceError(
            "Actuator executor must return a terminal status"
        )

    run_started_at = _normalize_database_datetime(
        run.started_at
    )

    event_started_at = _normalize_database_datetime(
        event.started_at
    )

    try:
        run_plan = build_automation_run_plan(
            started_at=run_started_at,
            completed_at=result.completed_at,
            trigger_value=run.trigger_value,
            status=result.status,
            result_summary=result.result_summary,
            error_message=result.error_message,
        )
    except AutomationServiceError as exc:
        raise AutomationRuntimeServiceError(
            "Actuator executor returned an invalid result"
        ) from exc

    completed_at = _normalize_database_datetime(
        result.completed_at
    )

    if completed_at < event_started_at:
        raise AutomationRuntimeServiceError(
            "Actuator completion time cannot be before start time"
        )

    duration_ms = int(
        round(
            (
                completed_at
                - event_started_at
            ).total_seconds()
            * 1000
        )
    )

    run.completed_at = run_plan.completed_at
    run.status = run_plan.status
    run.result_summary = (
        run_plan.result_summary
    )
    run.error_message = (
        run_plan.error_message
    )

    event.actual_value = (
        result.actual_value
    )
    event.completed_at = completed_at
    event.duration_ms = duration_ms
    event.status = result.status
    event.fault_code = result.fault_code
    event.error_message = (
        result.error_message
    )

    await session.commit()

    await session.refresh(run)
    await session.refresh(event)

    return records


async def _fail_execution_after_executor_error(
    session: AsyncSession,
    *,
    records: AutomationExecutionRecords,
    exc: Exception,
) -> None:
    run = records.automation_run
    event = records.actuator_event

    started_at = _normalize_database_datetime(
        event.started_at
    )

    now = datetime.now(
        timezone.utc
    )

    # Defensive protection for an injected/future test timestamp.
    completed_at = max(
        now,
        started_at,
    )

    error_message = (
        str(exc).strip()
        or "Actuator executor failed"
    )

    duration_ms = int(
        round(
            (
                completed_at
                - started_at
            ).total_seconds()
            * 1000
        )
    )

    run.completed_at = completed_at
    run.status = ExecutionStatus.FAILED
    run.result_summary = (
        "Automation actuator execution failed"
    )
    run.error_message = error_message

    event.completed_at = completed_at
    event.duration_ms = duration_ms
    event.status = ExecutionStatus.FAILED
    event.fault_code = None
    event.error_message = error_message

    await session.commit()

    await session.refresh(run)
    await session.refresh(event)


async def execute_automation_execution_records(
    session: AsyncSession,
    *,
    request: AutomationExecutionRequest,
    records: AutomationExecutionRecords,
    executor: ActuatorExecutor,
) -> AutomationExecutionRecords:
    _validate_execution_record_pair(
        request=request,
        records=records,
    )

    # Revalidate the actual target immediately before dispatch.
    _, actuator = await _validate_execution_request(
        session,
        request=request,
    )

    await _mark_execution_running(
        session,
        records=records,
    )

    command = ActuatorExecutionCommand(
        actuator_id=actuator.id,
        actuator_type=actuator.actuator_type,
        hardware_identifier=(
            actuator.hardware_identifier
        ),
        command_type=request.command_type,
        requested_value=(
            request.requested_value
        ),
    )

    try:
        result = await executor.execute(
            command
        )
    except Exception as exc:
        await _fail_execution_after_executor_error(
            session,
            records=records,
            exc=exc,
        )

        raise AutomationRuntimeServiceError(
            "Actuator execution failed"
        ) from exc

    try:
        return await _finalize_execution(
            session,
            records=records,
            result=result,
        )
    except AutomationRuntimeServiceError as exc:
        # An executor returning malformed/nonterminal output must
        # not leave the automation permanently RUNNING.
        await _fail_execution_after_executor_error(
            session,
            records=records,
            exc=exc,
        )

        raise


# ============================================================
# ACTUATOR STATE RECONCILIATION
# ============================================================


async def reconcile_automation_actuator_state(
    session: AsyncSession,
    *,
    request: AutomationExecutionRequest,
    records: AutomationExecutionRecords,
) -> Actuator:
    run = records.automation_run
    event = records.actuator_event

    if run.rule_id != request.rule_id:
        raise AutomationRuntimeServiceError(
            "Automation run does not match execution request"
        )

    if event.actuator_id != request.actuator_id:
        raise AutomationRuntimeServiceError(
            "Actuator event does not match execution request"
        )

    actuator = await session.get(
        Actuator,
        request.actuator_id,
    )

    if actuator is None:
        raise AutomationRuntimeServiceError(
            "Automation actuator not found"
        )

    # Only a confirmed successful terminal execution can update
    # the actuator's present-state snapshot.
    if (
        run.status
        != ExecutionStatus.COMPLETED
        or event.status
        != ExecutionStatus.COMPLETED
    ):
        return actuator

    if event.completed_at is None:
        raise AutomationRuntimeServiceError(
            "Completed actuator event requires completion time"
        )

    completed_at = _normalize_database_datetime(
        event.completed_at
    )

    if (
        event.command_type
        == ActuatorCommandType.ACTIVATE
    ):
        actuator.current_state = (
            ActuatorState.ON
        )

        # actual_value represents confirmed executor output.
        # Do not replace an existing state value with an
        # unverified requested value when actual output was
        # unavailable.
        if event.actual_value is not None:
            actuator.current_value = (
                event.actual_value
            )

        actuator.last_state_at = (
            completed_at
        )

    else:
        raise AutomationRuntimeServiceError(
            "Unsupported automation state reconciliation command"
        )

    await session.commit()
    await session.refresh(
        actuator
    )

    return actuator


# ============================================================
# EXECUTE + RECONCILE
# ============================================================


async def execute_and_reconcile_automation_execution(
    session: AsyncSession,
    *,
    request: AutomationExecutionRequest,
    records: AutomationExecutionRecords,
    executor: ActuatorExecutor,
) -> AutomationExecutionRecords:
    records = (
        await execute_automation_execution_records(
            session,
            request=request,
            records=records,
            executor=executor,
        )
    )

    await reconcile_automation_actuator_state(
        session,
        request=request,
        records=records,
    )

    return records