from __future__ import annotations

from datetime import datetime, timezone
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
from app.models.actuators import Actuator
from app.models.system import (
    AquaponicsSystem,
    User,
)
from app.schemas.actuator import (
    ActuatorCreate,
    ActuatorResponse,
    ActuatorUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/actuators",
    tags=["Actuators"],
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


def _actuator_audit_snapshot(
    actuator: Actuator,
) -> dict:
    return {
        "system_id": _audit_value(
            actuator.system_id
        ),
        "name": _audit_value(
            actuator.name
        ),
        "actuator_type": _audit_value(
            actuator.actuator_type
        ),
        "control_mode": _audit_value(
            actuator.control_mode
        ),
        "hardware_identifier": _audit_value(
            actuator.hardware_identifier
        ),
        "location_type": _audit_value(
            actuator.location_type
        ),
        "location_id": _audit_value(
            actuator.location_id
        ),
        "is_enabled": _audit_value(
            actuator.is_enabled
        ),
        "safety_config": _audit_value(
            actuator.safety_config
        ),
        "current_state": _audit_value(
            actuator.current_state
        ),
        "current_value": _audit_value(
            actuator.current_value
        ),
        "last_state_at": _audit_value(
            actuator.last_state_at
        ),
    }


# ============================================================
# CREATE
# ============================================================


@router.post(
    "",
    response_model=ActuatorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_actuator(
    payload: ActuatorCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> Actuator:
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

    actuator = Actuator(
        system_id=payload.system_id,
        name=payload.name,
        actuator_type=payload.actuator_type,
        control_mode=payload.control_mode,
        hardware_identifier=(
            payload.hardware_identifier
        ),
        location_type=payload.location_type,
        location_id=payload.location_id,
        is_enabled=payload.is_enabled,
        safety_config=payload.safety_config,
        current_state=payload.current_state,
        current_value=payload.current_value,
        last_state_at=payload.last_state_at,
    )

    session.add(
        actuator
    )

    await session.commit()
    await session.refresh(
        actuator
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="actuator",
        entity_id=actuator.id,
        new_value=(
            _actuator_audit_snapshot(
                actuator
            )
        ),
    )

    return actuator


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[ActuatorResponse],
)
async def list_actuators(
    system_id: UUID | None = Query(
        default=None
    ),
    include_deleted: bool = Query(
        default=False
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> list[Actuator]:
    stmt = select(
        Actuator
    )

    if system_id is not None:
        stmt = stmt.where(
            Actuator.system_id
            == system_id
        )

    if not include_deleted:
        stmt = stmt.where(
            Actuator.deleted_at.is_(None)
        )

    stmt = stmt.order_by(
        Actuator.created_at.desc()
    )

    result = await session.execute(
        stmt
    )

    return list(
        result.scalars().all()
    )


@router.get(
    "/{actuator_id}",
    response_model=ActuatorResponse,
)
async def get_actuator(
    actuator_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> Actuator:
    stmt = select(
        Actuator
    ).where(
        Actuator.id == actuator_id,
        Actuator.deleted_at.is_(None),
    )

    result = await session.execute(
        stmt
    )

    actuator = (
        result.scalar_one_or_none()
    )

    if actuator is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator not found",
        )

    return actuator


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{actuator_id}",
    response_model=ActuatorResponse,
)
async def update_actuator(
    actuator_id: UUID,
    payload: ActuatorUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> Actuator:
    stmt = select(
        Actuator
    ).where(
        Actuator.id == actuator_id,
        Actuator.deleted_at.is_(None),
    )

    result = await session.execute(
        stmt
    )

    actuator = (
        result.scalar_one_or_none()
    )

    if actuator is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator not found",
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    old_value = {
        field: _audit_value(
            getattr(
                actuator,
                field,
            )
        )
        for field in update_data
    }

    for field, value in update_data.items():
        setattr(
            actuator,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        actuator
    )

    new_value = {
        field: _audit_value(
            getattr(
                actuator,
                field,
            )
        )
        for field in update_data
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="actuator",
        entity_id=actuator.id,
        old_value=old_value,
        new_value=new_value,
    )

    return actuator


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{actuator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_actuator(
    actuator_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> None:
    stmt = select(
        Actuator
    ).where(
        Actuator.id == actuator_id,
        Actuator.deleted_at.is_(None),
    )

    result = await session.execute(
        stmt
    )

    actuator = (
        result.scalar_one_or_none()
    )

    if actuator is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator not found",
        )

    old_deleted_at = (
        actuator.deleted_at
    )

    deletion_time = datetime.now(
        timezone.utc
    )

    actuator.deleted_at = (
        deletion_time
    )

    await session.commit()
    await session.refresh(
        actuator
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="actuator",
        entity_id=actuator.id,
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