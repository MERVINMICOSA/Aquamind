from __future__ import annotations

from datetime import datetime, timezone
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
    GrowBed,
    User,
)
from app.schemas.grow_bed import (
    GrowBedCreate,
    GrowBedResponse,
    GrowBedUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/grow-beds",
    tags=["grow-beds"],
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

    if isinstance(value, Enum):
        return value.value

    return value


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[GrowBedResponse],
)
async def list_grow_beds(
    system_id: UUID | None = None,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    query = (
        select(GrowBed)
        .where(
            GrowBed.deleted_at.is_(None)
        )
        .order_by(
            GrowBed.name
        )
    )

    if system_id is not None:
        query = query.where(
            GrowBed.system_id
            == system_id
        )

    result = await session.execute(
        query
    )

    return result.scalars().all()


@router.get(
    "/{grow_bed_id}",
    response_model=GrowBedResponse,
)
async def get_grow_bed(
    grow_bed_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    grow_bed = await session.get(
        GrowBed,
        grow_bed_id,
    )

    if (
        grow_bed is None
        or grow_bed.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grow bed not found",
        )

    return grow_bed


# ============================================================
# CREATE
# ============================================================


@router.post(
    "",
    response_model=GrowBedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_grow_bed(
    payload: GrowBedCreate,
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

    grow_bed = GrowBed(
        system_id=payload.system_id,
        name=payload.name,
        crop_type=payload.crop_type,
        capacity_description=(
            payload.capacity_description
        ),
        is_active=payload.is_active,
    )

    session.add(grow_bed)

    await session.commit()
    await session.refresh(grow_bed)

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="grow_bed",
        entity_id=grow_bed.id,
        new_value={
            "system_id": _audit_value(
                grow_bed.system_id
            ),
            "name": _audit_value(
                grow_bed.name
            ),
            "crop_type": _audit_value(
                grow_bed.crop_type
            ),
            "capacity_description": _audit_value(
                grow_bed.capacity_description
            ),
            "is_active": _audit_value(
                grow_bed.is_active
            ),
        },
    )

    return grow_bed


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{grow_bed_id}",
    response_model=GrowBedResponse,
)
async def update_grow_bed(
    grow_bed_id: UUID,
    payload: GrowBedUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    grow_bed = await session.get(
        GrowBed,
        grow_bed_id,
    )

    if (
        grow_bed is None
        or grow_bed.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grow bed not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    old_value = {
        field: _audit_value(
            getattr(
                grow_bed,
                field,
            )
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            grow_bed,
            field,
            value,
        )

    await session.commit()
    await session.refresh(grow_bed)

    new_value = {
        field: _audit_value(
            getattr(
                grow_bed,
                field,
            )
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="grow_bed",
        entity_id=grow_bed.id,
        old_value=old_value,
        new_value=new_value,
    )

    return grow_bed


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{grow_bed_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_grow_bed(
    grow_bed_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    grow_bed = await session.get(
        GrowBed,
        grow_bed_id,
    )

    if (
        grow_bed is None
        or grow_bed.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grow bed not found",
        )

    old_deleted_at = (
        grow_bed.deleted_at
    )

    deletion_time = datetime.now(
        timezone.utc
    )

    grow_bed.deleted_at = (
        deletion_time
    )

    await session.commit()
    await session.refresh(grow_bed)

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="grow_bed",
        entity_id=grow_bed.id,
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