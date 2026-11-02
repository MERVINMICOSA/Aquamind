from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.other import AuditLog


class AuditServiceError(ValueError):
    """Raised when an audit log entry is invalid."""


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACKNOWLEDGE = "acknowledge"
    LOGIN = "login"
    LOGOUT = "logout"
    REFRESH = "refresh"


class AuditSource(str, Enum):
    API = "api"


def _validate_required_text(
    value: str,
    *,
    field_name: str,
    max_length: int,
) -> str:
    if not isinstance(value, str):
        raise AuditServiceError(
            f"{field_name} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise AuditServiceError(
            f"{field_name} cannot be empty"
        )

    if len(normalized) > max_length:
        raise AuditServiceError(
            f"{field_name} exceeds maximum length"
        )

    return normalized


def _validate_created_at(
    value: datetime,
) -> datetime:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise AuditServiceError(
            "Audit timestamp must be timezone-aware"
        )

    return value


async def create_audit_log(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: AuditAction | str,
    entity_type: str,
    entity_id: UUID | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    source: AuditSource | str = AuditSource.API,
    created_at: datetime | None = None,
) -> AuditLog:
    action_value = (
        action.value
        if isinstance(action, AuditAction)
        else action
    )

    source_value = (
        source.value
        if isinstance(source, AuditSource)
        else source
    )

    action_value = _validate_required_text(
        action_value,
        field_name="Audit action",
        max_length=100,
    )

    entity_type_value = _validate_required_text(
        entity_type,
        field_name="Audit entity type",
        max_length=100,
    )

    source_value = _validate_required_text(
        source_value,
        field_name="Audit source",
        max_length=64,
    )

    timestamp = (
        created_at
        or datetime.now(timezone.utc)
    )

    _validate_created_at(
        timestamp
    )

    if (
        old_value is not None
        and not isinstance(old_value, dict)
    ):
        raise AuditServiceError(
            "Audit old value must be a dictionary"
        )

    if (
        new_value is not None
        and not isinstance(new_value, dict)
    ):
        raise AuditServiceError(
            "Audit new value must be a dictionary"
        )

    record = AuditLog(
        user_id=user_id,
        action=action_value,
        entity_type=entity_type_value,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        source=source_value,
        created_at=timestamp,
    )

    session.add(record)

    await session.commit()
    await session.refresh(record)

    return record