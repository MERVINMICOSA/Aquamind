from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db_session,
    require_admin,
)
from app.models.system import (
    AquaponicsSystem,
    Reservoir,
    User,
)
from app.schemas.reservoir import (
    ReservoirCreate,
    ReservoirResponse,
    ReservoirUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/reservoirs",
    tags=["reservoirs"],
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

    return value


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[ReservoirResponse],
)
async def list_reservoirs(
    system_id: UUID | None = None,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    query = (
        select(Reservoir)
        .where(
            Reservoir.deleted_at.is_(None)
        )
        .order_by(
            Reservoir.name
        )
    )

    if system_id is not None:
        query = query.where(
            Reservoir.system_id
            == system_id
        )

    result = await session.execute(
        query
    )

    return result.scalars().all()


@router.get(
    "/{reservoir_id}",
    response_model=ReservoirResponse,
)
async def get_reservoir(
    reservoir_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
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

    return reservoir


# ============================================================
# CREATE
# ============================================================


@router.post(
    "",
    response_model=ReservoirResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservoir(
    payload: ReservoirCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
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

    reservoir = Reservoir(
        system_id=payload.system_id,
        name=payload.name,
        capacity_liters=payload.capacity_liters,
        is_active=payload.is_active,
    )

    session.add(
        reservoir
    )

    await session.commit()
    await session.refresh(
        reservoir
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="reservoir",
        entity_id=reservoir.id,
        new_value={
            "system_id": _audit_value(
                reservoir.system_id
            ),
            "name": _audit_value(
                reservoir.name
            ),
            "capacity_liters": _audit_value(
                reservoir.capacity_liters
            ),
            "is_active": _audit_value(
                reservoir.is_active
            ),
        },
    )

    return reservoir


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{reservoir_id}",
    response_model=ReservoirResponse,
)
async def update_reservoir(
    reservoir_id: UUID,
    payload: ReservoirUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
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

    updates = payload.model_dump(
        exclude_unset=True,
    )

    old_value = {
        field: _audit_value(
            getattr(
                reservoir,
                field,
            )
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            reservoir,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        reservoir
    )

    new_value = {
        field: _audit_value(
            getattr(
                reservoir,
                field,
            )
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="reservoir",
        entity_id=reservoir.id,
        old_value=old_value,
        new_value=new_value,
    )

    return reservoir


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{reservoir_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_reservoir(
    reservoir_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
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

    old_deleted_at = (
        reservoir.deleted_at
    )

    deletion_time = datetime.now(
        timezone.utc
    )

    reservoir.deleted_at = (
        deletion_time
    )

    await session.commit()
    await session.refresh(
        reservoir
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="reservoir",
        entity_id=reservoir.id,
        old_value={
            "deleted_at": _audit_value(
                old_deleted_at
            ),
        },
        new_value={
            "deleted_at": _audit_value(
                deletion_time
            ),
        },
    )