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
from app.models.sensors import Sensor
from app.models.system import (
    AquaponicsSystem,
    User,
)
from app.schemas.sensor import (
    SensorCreate,
    SensorResponse,
    SensorUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/sensors",
    tags=["Sensors"],
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
# CREATE
# ============================================================


@router.post(
    "",
    response_model=SensorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sensor(
    payload: SensorCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> Sensor:
    # ---------------------------------------------------------
    # Verify parent aquaponics system exists
    # ---------------------------------------------------------

    system_stmt = select(
        AquaponicsSystem
    ).where(
        AquaponicsSystem.id
        == payload.system_id,
        AquaponicsSystem.deleted_at.is_(
            None
        ),
    )

    result = await session.execute(
        system_stmt
    )

    system = (
        result.scalar_one_or_none()
    )

    if system is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquaponics system not found",
        )

    # ---------------------------------------------------------
    # Create sensor
    # ---------------------------------------------------------

    sensor = Sensor(
        system_id=payload.system_id,
        name=payload.name,
        sensor_type=payload.sensor_type,
        measurement_type=(
            payload.measurement_type
        ),
        location_type=payload.location_type,
        location_id=payload.location_id,
        unit=payload.unit,
        hardware_identifier=(
            payload.hardware_identifier
        ),
        is_simulated=payload.is_simulated,
        is_enabled=payload.is_enabled,
        sampling_interval_seconds=(
            payload.sampling_interval_seconds
        ),
        calibration_status=(
            payload.calibration_status
        ),
    )

    session.add(
        sensor
    )

    await session.commit()
    await session.refresh(
        sensor
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="sensor",
        entity_id=sensor.id,
        new_value={
            "system_id": _audit_value(
                sensor.system_id
            ),
            "name": _audit_value(
                sensor.name
            ),
            "sensor_type": _audit_value(
                sensor.sensor_type
            ),
            "measurement_type": _audit_value(
                sensor.measurement_type
            ),
            "location_type": _audit_value(
                sensor.location_type
            ),
            "location_id": _audit_value(
                sensor.location_id
            ),
            "unit": _audit_value(
                sensor.unit
            ),
            "hardware_identifier": _audit_value(
                sensor.hardware_identifier
            ),
            "is_simulated": _audit_value(
                sensor.is_simulated
            ),
            "is_enabled": _audit_value(
                sensor.is_enabled
            ),
            "sampling_interval_seconds": (
                _audit_value(
                    sensor.sampling_interval_seconds
                )
            ),
            "calibration_status": _audit_value(
                sensor.calibration_status
            ),
        },
    )

    return sensor


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[SensorResponse],
)
async def list_sensors(
    system_id: UUID | None = Query(
        default=None
    ),
    include_deleted: bool = Query(
        default=False
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> list[Sensor]:
    stmt = select(
        Sensor
    )

    if not include_deleted:
        stmt = stmt.where(
            Sensor.deleted_at.is_(None)
        )

    if system_id is not None:
        stmt = stmt.where(
            Sensor.system_id
            == system_id
        )

    stmt = stmt.order_by(
        Sensor.created_at.desc()
    )

    result = await session.execute(
        stmt
    )

    return list(
        result.scalars().all()
    )


@router.get(
    "/{sensor_id}",
    response_model=SensorResponse,
)
async def get_sensor(
    sensor_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> Sensor:
    stmt = select(
        Sensor
    ).where(
        Sensor.id == sensor_id,
        Sensor.deleted_at.is_(None),
    )

    result = await session.execute(
        stmt
    )

    sensor = (
        result.scalar_one_or_none()
    )

    if sensor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor not found",
        )

    return sensor


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{sensor_id}",
    response_model=SensorResponse,
)
async def update_sensor(
    sensor_id: UUID,
    payload: SensorUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> Sensor:
    stmt = select(
        Sensor
    ).where(
        Sensor.id == sensor_id,
        Sensor.deleted_at.is_(None),
    )

    result = await session.execute(
        stmt
    )

    sensor = (
        result.scalar_one_or_none()
    )

    if sensor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor not found",
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    old_value = {
        field: _audit_value(
            getattr(
                sensor,
                field,
            )
        )
        for field in update_data
    }

    for field, value in update_data.items():
        setattr(
            sensor,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        sensor
    )

    new_value = {
        field: _audit_value(
            getattr(
                sensor,
                field,
            )
        )
        for field in update_data
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="sensor",
        entity_id=sensor.id,
        old_value=old_value,
        new_value=new_value,
    )

    return sensor


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{sensor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_sensor(
    sensor_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> None:
    stmt = select(
        Sensor
    ).where(
        Sensor.id == sensor_id,
        Sensor.deleted_at.is_(None),
    )

    result = await session.execute(
        stmt
    )

    sensor = (
        result.scalar_one_or_none()
    )

    if sensor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor not found",
        )

    old_deleted_at = (
        sensor.deleted_at
    )

    deletion_time = datetime.now(
        timezone.utc
    )

    sensor.deleted_at = (
        deletion_time
    )

    await session.commit()
    await session.refresh(
        sensor
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="sensor",
        entity_id=sensor.id,
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