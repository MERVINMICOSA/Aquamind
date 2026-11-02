from __future__ import annotations

from datetime import datetime, timezone
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
from app.models.alerts import AlertThreshold
from app.models.system import User
from app.schemas.alert_threshold import (
    AlertThresholdCreate,
    AlertThresholdResponse,
    AlertThresholdUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/alert-thresholds",
    tags=["alert-thresholds"],
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


def _threshold_audit_snapshot(
    threshold: AlertThreshold,
) -> dict:
    return {
        "sensor_type": _audit_value(
            threshold.sensor_type
        ),
        "measurement_type": _audit_value(
            threshold.measurement_type
        ),
        "warning_low": _audit_value(
            threshold.warning_low
        ),
        "warning_high": _audit_value(
            threshold.warning_high
        ),
        "critical_low": _audit_value(
            threshold.critical_low
        ),
        "critical_high": _audit_value(
            threshold.critical_high
        ),
        "cooldown_seconds": _audit_value(
            threshold.cooldown_seconds
        ),
        "enabled": _audit_value(
            threshold.enabled
        ),
        "updated_by_user_id": _audit_value(
            threshold.updated_by_user_id
        ),
        "updated_at": _audit_value(
            threshold.updated_at
        ),
    }


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[AlertThresholdResponse],
)
async def list_alert_thresholds(
    sensor_type: str | None = None,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    query = (
        select(AlertThreshold)
        .order_by(
            AlertThreshold.sensor_type,
            AlertThreshold.measurement_type,
        )
    )

    if sensor_type is not None:
        query = query.where(
            AlertThreshold.sensor_type
            == sensor_type
        )

    result = await session.execute(
        query
    )

    return result.scalars().all()


@router.get(
    "/{threshold_id}",
    response_model=AlertThresholdResponse,
)
async def get_alert_threshold(
    threshold_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    threshold = await session.get(
        AlertThreshold,
        threshold_id,
    )

    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert threshold not found",
        )

    return threshold


# ============================================================
# CREATE
# ============================================================


@router.post(
    "",
    response_model=AlertThresholdResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_alert_threshold(
    payload: AlertThresholdCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    updated_at = datetime.now(
        timezone.utc
    )

    threshold = AlertThreshold(
        sensor_type=payload.sensor_type,
        measurement_type=(
            payload.measurement_type
        ),
        warning_low=payload.warning_low,
        warning_high=payload.warning_high,
        critical_low=payload.critical_low,
        critical_high=payload.critical_high,
        cooldown_seconds=(
            payload.cooldown_seconds
        ),
        enabled=payload.enabled,

        # The authenticated user is authoritative.
        # Never trust a client-supplied updater UUID.
        updated_by_user_id=current_user.id,
        updated_at=updated_at,
    )

    session.add(
        threshold
    )

    await session.commit()
    await session.refresh(
        threshold
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="alert_threshold",
        entity_id=threshold.id,
        new_value=(
            _threshold_audit_snapshot(
                threshold
            )
        ),
    )

    return threshold


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{threshold_id}",
    response_model=AlertThresholdResponse,
)
async def update_alert_threshold(
    threshold_id: UUID,
    payload: AlertThresholdUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    threshold = await session.get(
        AlertThreshold,
        threshold_id,
    )

    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert threshold not found",
        )

    updates = payload.model_dump(
        exclude_unset=True,
    )

    # updated_by_user_id must come from authentication,
    # never from the request body.
    updates.pop(
        "updated_by_user_id",
        None,
    )

    old_value = {
        field: _audit_value(
            getattr(
                threshold,
                field,
            )
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            threshold,
            field,
            value,
        )

    threshold.updated_by_user_id = (
        current_user.id
    )

    threshold.updated_at = datetime.now(
        timezone.utc
    )

    await session.commit()
    await session.refresh(
        threshold
    )

    new_value = {
        field: _audit_value(
            getattr(
                threshold,
                field,
            )
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="alert_threshold",
        entity_id=threshold.id,
        old_value=old_value,
        new_value=new_value,
    )

    return threshold


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{threshold_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_alert_threshold(
    threshold_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    threshold = await session.get(
        AlertThreshold,
        threshold_id,
    )

    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert threshold not found",
        )

    # Alert thresholds are hard-deleted, so preserve the
    # complete previous configuration before deletion.
    old_value = (
        _threshold_audit_snapshot(
            threshold
        )
    )

    entity_id = threshold.id

    await session.delete(
        threshold
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="alert_threshold",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )