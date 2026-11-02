from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db_session,
    require_admin,
)
from app.models.automation import (
    AutomationRule,
    AutomationRun,
)
from app.models.system import User
from app.schemas.automation_run import (
    AutomationRunCreate,
    AutomationRunResponse,
    AutomationRunUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/automation-runs",
    tags=["automation-runs"],
)


# ============================================================
# AUDIT HELPERS
# ============================================================


def _audit_value(
    value,
):
    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {
            str(key): _audit_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _audit_value(item)
            for item in value
        ]

    return value


def _automation_run_audit_snapshot(
    run: AutomationRun,
) -> dict:
    return {
        "rule_id": _audit_value(
            run.rule_id
        ),
        "started_at": _audit_value(
            run.started_at
        ),
        "completed_at": _audit_value(
            run.completed_at
        ),
        "trigger_value": _audit_value(
            run.trigger_value
        ),
        "status": _audit_value(
            run.status
        ),
        "result_summary": _audit_value(
            run.result_summary
        ),
        "error_message": _audit_value(
            run.error_message
        ),
    }


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[AutomationRunResponse],
)
async def list_automation_runs(
    rule_id: UUID | None = None,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    query = (
        select(AutomationRun)
        .order_by(
            AutomationRun.started_at.desc()
        )
    )

    if rule_id is not None:
        query = query.where(
            AutomationRun.rule_id
            == rule_id
        )

    result = await session.execute(
        query
    )

    return result.scalars().all()


@router.get(
    "/history",
    response_model=list[AutomationRunResponse],
)
async def list_automation_run_history(
    rule_id: UUID,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    rule = await session.get(
        AutomationRule,
        rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation rule not found",
        )

    query = (
        select(AutomationRun)
        .where(
            AutomationRun.rule_id
            == rule_id
        )
        .order_by(
            AutomationRun.started_at.desc(),
            AutomationRun.id.desc(),
        )
        .offset(
            offset
        )
        .limit(
            limit
        )
    )

    result = await session.execute(
        query
    )

    return result.scalars().all()


@router.get(
    "/{run_id}",
    response_model=AutomationRunResponse,
)
async def get_automation_run(
    run_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    run = await session.get(
        AutomationRun,
        run_id,
    )

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation run not found",
        )

    return run


# ============================================================
# CREATE
#
# Runtime execution history.
# Protected by the application-level authenticated dependency,
# but intentionally not admin-only and not duplicated into
# AuditLog.
# ============================================================


@router.post(
    "",
    response_model=AutomationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_automation_run(
    payload: AutomationRunCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    rule = await session.get(
        AutomationRule,
        payload.rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation rule not found",
        )

    run = AutomationRun(
        rule_id=payload.rule_id,
        started_at=payload.started_at,
        completed_at=payload.completed_at,
        trigger_value=payload.trigger_value,
        status=payload.status,
        result_summary=payload.result_summary,
        error_message=payload.error_message,
    )

    session.add(
        run
    )

    await session.commit()
    await session.refresh(
        run
    )

    return run


# ============================================================
# UPDATE
#
# Runtime execution completion/status update.
# AutomationRun remains the canonical execution history, so
# these updates are not duplicated into AuditLog.
# ============================================================


@router.patch(
    "/{run_id}",
    response_model=AutomationRunResponse,
)
async def update_automation_run(
    run_id: UUID,
    payload: AutomationRunUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    run = await session.get(
        AutomationRun,
        run_id,
    )

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation run not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    for field, value in updates.items():
        setattr(
            run,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        run
    )

    return run


# ============================================================
# DELETE
#
# Destructive operation against runtime history.
# Administrator-only and audited before hard deletion.
# ============================================================


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_automation_run(
    run_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    run = await session.get(
        AutomationRun,
        run_id,
    )

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation run not found",
        )

    old_value = (
        _automation_run_audit_snapshot(
            run
        )
    )

    entity_id = run.id

    await session.delete(
        run
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="automation_run",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )