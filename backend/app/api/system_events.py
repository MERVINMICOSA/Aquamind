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
from app.db.enums import SystemEventSeverity
from app.models.other import SystemEvent
from app.models.system import (
    AquaponicsSystem,
    User,
)
from app.schemas.system_event import (
    SystemEventCreate,
    SystemEventResponse,
    SystemEventUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/system-events",
    tags=["System Events"],
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


def _system_event_audit_snapshot(
    event: SystemEvent,
) -> dict:
    return {
        "system_id": _audit_value(
            event.system_id
        ),
        "event_type": _audit_value(
            event.event_type
        ),
        "severity": _audit_value(
            event.severity
        ),
        "message": _audit_value(
            event.message
        ),
        "event_metadata": _audit_value(
            event.event_metadata
        ),
        "occurred_at": _audit_value(
            event.occurred_at
        ),
    }


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[SystemEventResponse],
)
async def list_system_events(
    system_id: UUID | None = Query(
        default=None
    ),
    severity: SystemEventSeverity | None = Query(
        default=None
    ),
    event_type: str | None = Query(
        default=None
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> list[SystemEvent]:
    stmt = select(
        SystemEvent
    )

    if system_id is not None:
        stmt = stmt.where(
            SystemEvent.system_id
            == system_id
        )

    if severity is not None:
        stmt = stmt.where(
            SystemEvent.severity
            == severity
        )

    if event_type is not None:
        stmt = stmt.where(
            SystemEvent.event_type
            == event_type
        )

    stmt = stmt.order_by(
        SystemEvent.occurred_at.desc()
    )

    result = await session.execute(
        stmt
    )

    return list(
        result.scalars().all()
    )


@router.get(
    "/{event_id}",
    response_model=SystemEventResponse,
)
async def get_system_event(
    event_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> SystemEvent:
    event = await session.get(
        SystemEvent,
        event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System event not found",
        )

    return event


# ============================================================
# CREATE
#
# Runtime/system history.
# Intentionally not admin-only and not duplicated into
# AuditLog.
# ============================================================


@router.post(
    "",
    response_model=SystemEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_system_event(
    payload: SystemEventCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> SystemEvent:
    system = await session.get(
        AquaponicsSystem,
        payload.system_id,
    )

    if (
        system is None
        or system.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquaponics system not found",
        )

    event = SystemEvent(
        system_id=payload.system_id,
        event_type=payload.event_type,
        severity=payload.severity,
        message=payload.message,
        event_metadata=(
            payload.event_metadata
        ),
        occurred_at=payload.occurred_at,
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
# Runtime/history correction or enrichment.
# SystemEvent remains the canonical history record.
# ============================================================


@router.patch(
    "/{event_id}",
    response_model=SystemEventResponse,
)
async def update_system_event(
    event_id: UUID,
    payload: SystemEventUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> SystemEvent:
    event = await session.get(
        SystemEvent,
        event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System event not found",
        )

    updates = payload.model_dump(
        exclude_unset=True,
    )

    for field, value in updates.items():
        if (
            value is None
            and field != "event_metadata"
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    f"{field} cannot be null"
                ),
            )

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
# Destructive removal of system history.
# Administrator-only and audited before hard deletion.
# ============================================================


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_system_event(
    event_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> None:
    event = await session.get(
        SystemEvent,
        event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System event not found",
        )

    old_value = (
        _system_event_audit_snapshot(
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
        entity_type="system_event",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )