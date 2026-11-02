from __future__ import annotations

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
    User,
)
from app.schemas.system import (
    SystemCreate,
    SystemResponse,
    SystemUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/systems",
    tags=["systems"],
)


@router.get(
    "",
    response_model=list[SystemResponse],
)
async def list_systems(
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(AquaponicsSystem)
        .where(
            AquaponicsSystem.deleted_at.is_(None)
        )
        .order_by(
            AquaponicsSystem.name
        )
    )

    return result.scalars().all()


@router.get(
    "/{system_id}",
    response_model=SystemResponse,
)
async def get_system(
    system_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    system = await session.get(
        AquaponicsSystem,
        system_id,
    )

    if (
        system is None
        or system.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquaponics system not found",
        )

    return system


@router.post(
    "",
    response_model=SystemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_system(
    payload: SystemCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    system = AquaponicsSystem(
        name=payload.name,
        description=payload.description,
        timezone=payload.timezone,
        is_active=payload.is_active,
    )

    session.add(system)

    await session.commit()
    await session.refresh(system)

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="system",
        entity_id=system.id,
        new_value={
            "name": system.name,
            "description": system.description,
            "timezone": system.timezone,
            "is_active": system.is_active,
        },
    )

    return system


@router.patch(
    "/{system_id}",
    response_model=SystemResponse,
)
async def update_system(
    system_id: UUID,
    payload: SystemUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    system = await session.get(
        AquaponicsSystem,
        system_id,
    )

    if (
        system is None
        or system.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquaponics system not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    old_value = {
        field: getattr(
            system,
            field,
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            system,
            field,
            value,
        )

    await session.commit()
    await session.refresh(system)

    new_value = {
        field: getattr(
            system,
            field,
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="system",
        entity_id=system.id,
        old_value=old_value,
        new_value=new_value,
    )

    return system