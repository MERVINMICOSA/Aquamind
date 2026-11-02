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
    Tank,
    User,
)
from app.schemas.tank import (
    TankCreate,
    TankResponse,
    TankUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/tanks",
    tags=["tanks"],
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
    response_model=list[TankResponse],
)
async def list_tanks(
    system_id: UUID | None = None,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    query = (
        select(Tank)
        .where(
            Tank.deleted_at.is_(None)
        )
        .order_by(
            Tank.name
        )
    )

    if system_id is not None:
        query = query.where(
            Tank.system_id
            == system_id
        )

    result = await session.execute(
        query
    )

    return result.scalars().all()


@router.get(
    "/{tank_id}",
    response_model=TankResponse,
)
async def get_tank(
    tank_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    tank = await session.get(
        Tank,
        tank_id,
    )

    if (
        tank is None
        or tank.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tank not found",
        )

    return tank


# ============================================================
# CREATE
# ============================================================


@router.post(
    "",
    response_model=TankResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tank(
    payload: TankCreate,
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

    tank = Tank(
        system_id=payload.system_id,
        name=payload.name,
        capacity_liters=payload.capacity_liters,
        species=payload.species,
        is_active=payload.is_active,
    )

    session.add(tank)

    await session.commit()
    await session.refresh(tank)

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="tank",
        entity_id=tank.id,
        new_value={
            "system_id": _audit_value(
                tank.system_id
            ),
            "name": _audit_value(
                tank.name
            ),
            "capacity_liters": _audit_value(
                tank.capacity_liters
            ),
            "species": _audit_value(
                tank.species
            ),
            "is_active": _audit_value(
                tank.is_active
            ),
        },
    )

    return tank


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{tank_id}",
    response_model=TankResponse,
)
async def update_tank(
    tank_id: UUID,
    payload: TankUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    tank = await session.get(
        Tank,
        tank_id,
    )

    if (
        tank is None
        or tank.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tank not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    old_value = {
        field: _audit_value(
            getattr(
                tank,
                field,
            )
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            tank,
            field,
            value,
        )

    await session.commit()
    await session.refresh(tank)

    new_value = {
        field: _audit_value(
            getattr(
                tank,
                field,
            )
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="tank",
        entity_id=tank.id,
        old_value=old_value,
        new_value=new_value,
    )

    return tank


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{tank_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tank(
    tank_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    tank = await session.get(
        Tank,
        tank_id,
    )

    if (
        tank is None
        or tank.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tank not found",
        )

    old_deleted_at = tank.deleted_at

    deletion_time = datetime.now(
        timezone.utc
    )

    tank.deleted_at = deletion_time

    await session.commit()
    await session.refresh(tank)

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="tank",
        entity_id=tank.id,
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