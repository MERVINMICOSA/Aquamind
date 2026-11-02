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
    get_current_user,
    get_db_session,
    require_admin,
)
from app.db.enums import (
    AlertStatus,
)
from app.models.actuators import Actuator
from app.models.alerts import Alert
from app.models.sensors import Sensor
from app.models.system import (
    AquaponicsSystem,
    User,
)
from app.schemas.alert import (
    AlertCreate,
    AlertResponse,
    AlertUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
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


def _alert_audit_snapshot(
    alert: Alert,
) -> dict:
    return {
        "system_id": _audit_value(
            alert.system_id
        ),
        "sensor_id": _audit_value(
            alert.sensor_id
        ),
        "actuator_id": _audit_value(
            alert.actuator_id
        ),
        "alert_type": _audit_value(
            alert.alert_type
        ),
        "severity": _audit_value(
            alert.severity
        ),
        "message": _audit_value(
            alert.message
        ),
        "trigger_value": _audit_value(
            alert.trigger_value
        ),
        "threshold_id": _audit_value(
            alert.threshold_id
        ),
        "status": _audit_value(
            alert.status
        ),
        "created_at": _audit_value(
            alert.created_at
        ),
        "acknowledged_at": _audit_value(
            alert.acknowledged_at
        ),
        "acknowledged_by_user_id": (
            _audit_value(
                alert.acknowledged_by_user_id
            )
        ),
        "resolved_at": _audit_value(
            alert.resolved_at
        ),
        "resolution_reason": _audit_value(
            alert.resolution_reason
        ),
    }


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[AlertResponse],
)
async def list_alerts(
    system_id: UUID | None = None,
    sensor_id: UUID | None = None,
    actuator_id: UUID | None = None,
    alert_status: AlertStatus | None = None,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    query = (
        select(Alert)
        .order_by(
            Alert.created_at.desc()
        )
    )

    if system_id is not None:
        query = query.where(
            Alert.system_id
            == system_id
        )

    if sensor_id is not None:
        query = query.where(
            Alert.sensor_id
            == sensor_id
        )

    if actuator_id is not None:
        query = query.where(
            Alert.actuator_id
            == actuator_id
        )

    if alert_status is not None:
        query = query.where(
            Alert.status
            == alert_status
        )

    result = await session.execute(
        query
    )

    return result.scalars().all()


@router.get(
    "/history",
    response_model=list[AlertResponse],
)
async def list_alert_history(
    system_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[Alert]:
    """Return a bounded page of persisted alerts for one system."""
    system = await session.get(AquaponicsSystem, system_id)
    if system is None or system.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquaponics system not found",
        )

    query = (
        select(Alert)
        .where(Alert.system_id == system_id)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
)
async def get_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    alert = await session.get(
        Alert,
        alert_id,
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return alert


# ============================================================
# CREATE
#
# Runtime alert creation.
# Authenticated by the application-level router dependency,
# but intentionally NOT admin-only and NOT duplicated into
# AuditLog.
# ============================================================


@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_alert(
    payload: AlertCreate,
    session: AsyncSession = Depends(
        get_db_session
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

    if payload.sensor_id is not None:
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

        if (
            sensor.system_id
            != payload.system_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Sensor does not belong "
                    "to the specified system"
                ),
            )

    if payload.actuator_id is not None:
        actuator = await session.get(
            Actuator,
            payload.actuator_id,
        )

        if (
            actuator is None
            or actuator.deleted_at is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Actuator not found",
            )

        if (
            actuator.system_id
            != payload.system_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Actuator does not belong "
                    "to the specified system"
                ),
            )

    alert = Alert(
        system_id=payload.system_id,
        sensor_id=payload.sensor_id,
        actuator_id=payload.actuator_id,
        alert_type=payload.alert_type,
        severity=payload.severity,
        message=payload.message,
        trigger_value=payload.trigger_value,
        threshold_id=payload.threshold_id,
        status=payload.status,
        created_at=datetime.now(
            timezone.utc
        ),
    )

    session.add(
        alert
    )

    await session.commit()
    await session.refresh(
        alert
    )

    return alert


# ============================================================
# UPDATE / LIFECYCLE
# ============================================================


@router.patch(
    "/{alert_id}",
    response_model=AlertResponse,
)
async def update_alert(
    alert_id: UUID,
    payload: AlertUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    alert = await session.get(
        Alert,
        alert_id,
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    # --------------------------------------------------------
    # Lifecycle ownership belongs to the server/authenticated
    # user. These request fields remain in the schema for
    # compatibility but are not trusted as authoritative.
    # --------------------------------------------------------

    updates.pop(
        "acknowledged_at",
        None,
    )

    updates.pop(
        "acknowledged_by_user_id",
        None,
    )

    updates.pop(
        "resolved_at",
        None,
    )

    previous_status = (
        alert.status
    )

    audit_fields = set(
        updates.keys()
    )

    requested_status = (
        updates.get("status")
    )

    if (
        requested_status
        == AlertStatus.ACKNOWLEDGED
    ):
        audit_fields.update(
            {
                "acknowledged_at",
                "acknowledged_by_user_id",
            }
        )

    if (
        requested_status
        == AlertStatus.RESOLVED
    ):
        audit_fields.add(
            "resolved_at"
        )

    old_value = {
        field: _audit_value(
            getattr(
                alert,
                field,
            )
        )
        for field in audit_fields
    }

    # --------------------------------------------------------
    # Apply client-controlled update fields.
    # --------------------------------------------------------

    for field, value in updates.items():
        setattr(
            alert,
            field,
            value,
        )

    # --------------------------------------------------------
    # Apply server-controlled lifecycle metadata.
    # --------------------------------------------------------

    if (
        requested_status
        == AlertStatus.ACKNOWLEDGED
    ):
        now = datetime.now(
            timezone.utc
        )

        if alert.acknowledged_at is None:
            alert.acknowledged_at = now

        if (
            alert.acknowledged_by_user_id
            is None
        ):
            alert.acknowledged_by_user_id = (
                current_user.id
            )

    elif (
        requested_status
        == AlertStatus.RESOLVED
    ):
        if alert.resolved_at is None:
            alert.resolved_at = (
                datetime.now(
                    timezone.utc
                )
            )

    await session.commit()
    await session.refresh(
        alert
    )

    if audit_fields:
        new_value = {
            field: _audit_value(
                getattr(
                    alert,
                    field,
                )
            )
            for field in audit_fields
        }

        audit_action = (
            AuditAction.ACKNOWLEDGE
            if (
                requested_status
                == AlertStatus.ACKNOWLEDGED
                and previous_status
                != AlertStatus.ACKNOWLEDGED
            )
            else AuditAction.UPDATE
        )

        await create_audit_log(
            session,
            user_id=current_user.id,
            action=audit_action,
            entity_type="alert",
            entity_id=alert.id,
            old_value=old_value,
            new_value=new_value,
        )

    return alert


# ============================================================
# DELETE
#
# Destructive administrative operation.
# Alerts are hard-deleted, so preserve their complete previous
# state before deleting the canonical Alert row.
# ============================================================


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    alert = await session.get(
        Alert,
        alert_id,
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    old_value = (
        _alert_audit_snapshot(
            alert
        )
    )

    entity_id = alert.id

    await session.delete(
        alert
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="alert",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )
