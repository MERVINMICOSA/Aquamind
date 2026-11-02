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
from app.models.refill import RefillEvent
from app.models.system import (
    AquaponicsSystem,
    Reservoir,
    Tank,
    User,
)
from app.schemas.refill import (
    RefillEventCreate,
    RefillEventResponse,
    RefillEventUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/refill-events",
    tags=["Refill Events"],
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


def _refill_event_audit_snapshot(
    event: RefillEvent,
) -> dict:
    return {
        "reservoir_id": _audit_value(
            event.reservoir_id
        ),
        "target_tank_id": _audit_value(
            event.target_tank_id
        ),
        "start_level_percent": _audit_value(
            event.start_level_percent
        ),
        "end_level_percent": _audit_value(
            event.end_level_percent
        ),
        "started_at": _audit_value(
            event.started_at
        ),
        "completed_at": _audit_value(
            event.completed_at
        ),
        "duration_seconds": _audit_value(
            event.duration_seconds
        ),
        "trigger": _audit_value(
            event.trigger
        ),
        "status": _audit_value(
            event.status
        ),
        "timeout_reason": _audit_value(
            event.timeout_reason
        ),
    }


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[RefillEventResponse],
)
async def list_refill_events(
    reservoir_id: UUID | None = Query(
        default=None
    ),
    target_tank_id: UUID | None = Query(
        default=None
    ),
    status_filter: str | None = Query(
        default=None
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> list[RefillEvent]:
    stmt = select(
        RefillEvent
    )

    if reservoir_id is not None:
        stmt = stmt.where(
            RefillEvent.reservoir_id
            == reservoir_id
        )

    if target_tank_id is not None:
        stmt = stmt.where(
            RefillEvent.target_tank_id
            == target_tank_id
        )

    if status_filter is not None:
        stmt = stmt.where(
            RefillEvent.status
            == status_filter
        )

    stmt = stmt.order_by(
        RefillEvent.started_at.desc()
    )

    result = await session.execute(
        stmt
    )

    return list(
        result.scalars().all()
    )


@router.get(
    "/history",
    response_model=list[RefillEventResponse],
)
async def list_refill_event_history(
    reservoir_id: UUID,
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
) -> list[RefillEvent]:
    reservoir = await session.get(
        Reservoir,
        reservoir_id,
    )

    if (
        reservoir is None
        or reservoir.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservoir not found",
        )

    stmt = (
        select(RefillEvent)
        .where(
            RefillEvent.reservoir_id
            == reservoir_id
        )
        .order_by(
            RefillEvent.started_at.desc(),
            RefillEvent.id.desc(),
        )
        .offset(
            offset
        )
        .limit(
            limit
        )
    )

    result = await session.execute(
        stmt
    )

    return list(
        result.scalars().all()
    )

@router.get(
    "/{refill_event_id}",
    response_model=RefillEventResponse,
)
async def get_refill_event(
    refill_event_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> RefillEvent:
    event = await session.get(
        RefillEvent,
        refill_event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refill event not found",
        )

    return event


# ============================================================
# CREATE
#
# Runtime refill execution history.
# Intentionally not admin-only and not duplicated into
# AuditLog.
# ============================================================


@router.post(
    "",
    response_model=RefillEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_refill_event(
    payload: RefillEventCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> RefillEvent:
    reservoir = await session.get(
        Reservoir,
        payload.reservoir_id,
    )

    if (
        reservoir is None
        or reservoir.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservoir not found",
        )

    tank = await session.get(
        Tank,
        payload.target_tank_id,
    )

    if (
        tank is None
        or tank.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target tank not found",
        )

    if (
        reservoir.system_id
        != tank.system_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Reservoir and target tank "
                "must belong to the same system"
            ),
        )

    system = await session.get(
        AquaponicsSystem,
        reservoir.system_id,
    )

    if (
        system is None
        or system.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquaponics system not found",
        )

    event = RefillEvent(
        reservoir_id=payload.reservoir_id,
        target_tank_id=(
            payload.target_tank_id
        ),
        start_level_percent=(
            payload.start_level_percent
        ),
        end_level_percent=(
            payload.end_level_percent
        ),
        started_at=payload.started_at,
        completed_at=payload.completed_at,
        duration_seconds=(
            payload.duration_seconds
        ),
        trigger=payload.trigger,
        status=payload.status,
        timeout_reason=(
            payload.timeout_reason
        ),
    )

    session.add(
        event
    )

    await session.commit()
    await session.refresh(
        event
    )

    return event


# ============================================================
# UPDATE
#
# Runtime completion/status update.
# RefillEvent remains the canonical execution history.
# ============================================================


@router.patch(
    "/{refill_event_id}",
    response_model=RefillEventResponse,
)
async def update_refill_event(
    refill_event_id: UUID,
    payload: RefillEventUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> RefillEvent:
    event = await session.get(
        RefillEvent,
        refill_event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refill event not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    reservoir_id = updates.get(
        "reservoir_id",
        event.reservoir_id,
    )

    target_tank_id = updates.get(
        "target_tank_id",
        event.target_tank_id,
    )

    reservoir = await session.get(
        Reservoir,
        reservoir_id,
    )

    if (
        reservoir is None
        or reservoir.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservoir not found",
        )

    tank = await session.get(
        Tank,
        target_tank_id,
    )

    if (
        tank is None
        or tank.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target tank not found",
        )

    if (
        reservoir.system_id
        != tank.system_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Reservoir and target tank "
                "must belong to the same system"
            ),
        )

    for field, value in updates.items():
        setattr(
            event,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        event
    )

    return event


# ============================================================
# DELETE
#
# Destructive removal of runtime history.
# Administrator-only and audited before hard deletion.
# ============================================================


@router.delete(
    "/{refill_event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_refill_event(
    refill_event_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> None:
    event = await session.get(
        RefillEvent,
        refill_event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refill event not found",
        )

    old_value = (
        _refill_event_audit_snapshot(
            event
        )
    )

    entity_id = event.id

    await session.delete(
        event
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="refill_event",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )