from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db_session,
    require_admin,
)
from app.models.sensors import (
    Sensor,
    SensorCalibration,
)
from app.models.system import User
from app.schemas.sensor_calibration import (
    SensorCalibrationCreate,
    SensorCalibrationResponse,
    SensorCalibrationUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/sensor-calibrations",
    tags=["sensor-calibrations"],
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


def _calibration_audit_snapshot(
    calibration: SensorCalibration,
) -> dict:
    return {
        "sensor_id": _audit_value(
            calibration.sensor_id
        ),
        "offset": _audit_value(
            calibration.offset
        ),
        "factor": _audit_value(
            calibration.factor
        ),
        "calibration_data": _audit_value(
            calibration.calibration_data
        ),
        "performed_at": _audit_value(
            calibration.performed_at
        ),
        "verified_by_user_id": _audit_value(
            calibration.verified_by_user_id
        ),
        "status": _audit_value(
            calibration.status
        ),
        "notes": _audit_value(
            calibration.notes
        ),
    }


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[SensorCalibrationResponse],
)
async def list_sensor_calibrations(
    sensor_id: UUID | None = None,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    query = (
        select(SensorCalibration)
        .order_by(
            SensorCalibration.performed_at.desc()
        )
    )

    if sensor_id is not None:
        query = query.where(
            SensorCalibration.sensor_id
            == sensor_id
        )

    result = await session.execute(
        query
    )

    return result.scalars().all()


@router.get(
    "/{calibration_id}",
    response_model=SensorCalibrationResponse,
)
async def get_sensor_calibration(
    calibration_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    calibration = await session.get(
        SensorCalibration,
        calibration_id,
    )

    if calibration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor calibration not found",
        )

    return calibration


# ============================================================
# CREATE
# ============================================================


@router.post(
    "",
    response_model=SensorCalibrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sensor_calibration(
    payload: SensorCalibrationCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    sensor = await session.get(
        Sensor,
        payload.sensor_id,
    )

    if (
        sensor is None
        or sensor.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor not found",
        )

    calibration = SensorCalibration(
        sensor_id=payload.sensor_id,
        offset=payload.offset,
        factor=payload.factor,
        calibration_data=(
            payload.calibration_data
        ),
        performed_at=payload.performed_at,
        verified_by_user_id=(
            payload.verified_by_user_id
        ),
        status=payload.status,
        notes=payload.notes,
    )

    session.add(
        calibration
    )

    await session.commit()
    await session.refresh(
        calibration
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="sensor_calibration",
        entity_id=calibration.id,
        new_value=(
            _calibration_audit_snapshot(
                calibration
            )
        ),
    )

    return calibration


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{calibration_id}",
    response_model=SensorCalibrationResponse,
)
async def update_sensor_calibration(
    calibration_id: UUID,
    payload: SensorCalibrationUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    calibration = await session.get(
        SensorCalibration,
        calibration_id,
    )

    if calibration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor calibration not found",
        )

    updates = payload.model_dump(
        exclude_unset=True,
    )

    old_value = {
        field: _audit_value(
            getattr(
                calibration,
                field,
            )
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            calibration,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        calibration
    )

    new_value = {
        field: _audit_value(
            getattr(
                calibration,
                field,
            )
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="sensor_calibration",
        entity_id=calibration.id,
        old_value=old_value,
        new_value=new_value,
    )

    return calibration


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{calibration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_sensor_calibration(
    calibration_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    calibration = await session.get(
        SensorCalibration,
        calibration_id,
    )

    if calibration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor calibration not found",
        )

    # Sensor calibrations are hard-deleted, so capture
    # their state before removing the database row.
    old_value = (
        _calibration_audit_snapshot(
            calibration
        )
    )

    entity_id = calibration.id

    await session.delete(
        calibration
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="sensor_calibration",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )