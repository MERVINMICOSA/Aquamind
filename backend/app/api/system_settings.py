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
from app.models.system import (
    AquaponicsSystem,
    SystemSetting,
    User,
)
from app.schemas.system_setting import (
    SystemSettingCreate,
    SystemSettingResponse,
    SystemSettingUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/system-settings",
    tags=["System Settings"],
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


def _system_setting_audit_snapshot(
    setting: SystemSetting,
) -> dict:
    return {
        "system_id": _audit_value(
            setting.system_id
        ),
        "setting_key": _audit_value(
            setting.setting_key
        ),
        "setting_value": _audit_value(
            setting.setting_value
        ),
        "value_type": _audit_value(
            setting.value_type
        ),
        "updated_at": _audit_value(
            setting.updated_at
        ),
        "updated_by_user_id": _audit_value(
            setting.updated_by_user_id
        ),
        "deleted_at": _audit_value(
            setting.deleted_at
        ),
    }


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[SystemSettingResponse],
)
async def list_system_settings(
    system_id: UUID | None = Query(
        default=None
    ),
    setting_key: str | None = Query(
        default=None
    ),
    include_deleted: bool = Query(
        default=False
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> list[SystemSetting]:
    stmt = select(
        SystemSetting
    )

    if not include_deleted:
        stmt = stmt.where(
            SystemSetting.deleted_at.is_(None)
        )

    if system_id is not None:
        stmt = stmt.where(
            SystemSetting.system_id
            == system_id
        )

    if setting_key is not None:
        stmt = stmt.where(
            SystemSetting.setting_key
            == setting_key
        )

    stmt = stmt.order_by(
        SystemSetting.setting_key
    )

    result = await session.execute(
        stmt
    )

    return list(
        result.scalars().all()
    )


@router.get(
    "/{setting_id}",
    response_model=SystemSettingResponse,
)
async def get_system_setting(
    setting_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> SystemSetting:
    setting = await session.get(
        SystemSetting,
        setting_id,
    )

    if (
        setting is None
        or setting.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System setting not found",
        )

    return setting


# ============================================================
# CREATE
# ============================================================


@router.post(
    "",
    response_model=SystemSettingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_system_setting(
    payload: SystemSettingCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> SystemSetting:
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

    result = await session.execute(
        select(SystemSetting).where(
            SystemSetting.system_id
            == payload.system_id,
            SystemSetting.setting_key
            == payload.setting_key,
        )
    )

    existing = (
        result.scalar_one_or_none()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "System setting with this key "
                "already exists"
            ),
        )

    now = datetime.now(
        timezone.utc
    )

    setting = SystemSetting(
        system_id=payload.system_id,
        setting_key=payload.setting_key,
        setting_value=payload.setting_value,
        value_type=payload.value_type,
        updated_at=now,
        updated_by_user_id=(
            current_user.id
        ),
        deleted_at=None,
    )

    session.add(
        setting
    )

    await session.commit()
    await session.refresh(
        setting
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="system_setting",
        entity_id=setting.id,
        new_value=(
            _system_setting_audit_snapshot(
                setting
            )
        ),
    )

    return setting


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{setting_id}",
    response_model=SystemSettingResponse,
)
async def update_system_setting(
    setting_id: UUID,
    payload: SystemSettingUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> SystemSetting:
    setting = await session.get(
        SystemSetting,
        setting_id,
    )

    if (
        setting is None
        or setting.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System setting not found",
        )

    updates = payload.model_dump(
        exclude_unset=True,
    )

    for field, value in updates.items():
        if value is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    f"{field} cannot be null"
                ),
            )

    new_key = updates.get(
        "setting_key",
        setting.setting_key,
    )

    if new_key != setting.setting_key:
        result = await session.execute(
            select(SystemSetting).where(
                SystemSetting.system_id
                == setting.system_id,
                SystemSetting.setting_key
                == new_key,
                SystemSetting.id
                != setting.id,
            )
        )

        duplicate = (
            result.scalar_one_or_none()
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "System setting with this key "
                    "already exists"
                ),
            )

    audit_fields = set(
        updates.keys()
    )

    audit_fields.update(
        {
            "updated_at",
            "updated_by_user_id",
        }
    )

    old_value = {
        field: _audit_value(
            getattr(
                setting,
                field,
            )
        )
        for field in audit_fields
    }

    for field, value in updates.items():
        setattr(
            setting,
            field,
            value,
        )

    setting.updated_at = datetime.now(
        timezone.utc
    )

    setting.updated_by_user_id = (
        current_user.id
    )

    await session.commit()
    await session.refresh(
        setting
    )

    new_value = {
        field: _audit_value(
            getattr(
                setting,
                field,
            )
        )
        for field in audit_fields
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="system_setting",
        entity_id=setting.id,
        old_value=old_value,
        new_value=new_value,
    )

    return setting


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{setting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_system_setting(
    setting_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
) -> None:
    setting = await session.get(
        SystemSetting,
        setting_id,
    )

    if (
        setting is None
        or setting.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System setting not found",
        )

    old_value = {
        "deleted_at": _audit_value(
            setting.deleted_at
        ),
        "updated_at": _audit_value(
            setting.updated_at
        ),
        "updated_by_user_id": _audit_value(
            setting.updated_by_user_id
        ),
    }

    now = datetime.now(
        timezone.utc
    )

    setting.deleted_at = now
    setting.updated_at = now
    setting.updated_by_user_id = (
        current_user.id
    )

    await session.commit()
    await session.refresh(
        setting
    )

    new_value = {
        "deleted_at": _audit_value(
            setting.deleted_at
        ),
        "updated_at": _audit_value(
            setting.updated_at
        ),
        "updated_by_user_id": _audit_value(
            setting.updated_by_user_id
        ),
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="system_setting",
        entity_id=setting.id,
        old_value=old_value,
        new_value=new_value,
    )