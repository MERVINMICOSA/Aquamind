from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import RefreshToken, User
from app.services.security_service import (
    RefreshTokenSecurityError,
    create_refresh_token_material,
    hash_refresh_token,
)


# ============================================================
# EXCEPTIONS
# ============================================================


class RefreshTokenLifecycleError(ValueError):
    """Raised when a persisted refresh token cannot be used safely."""


# ============================================================
# DATA OBJECTS
# ============================================================


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    token: str

    record_id: UUID
    user_id: UUID

    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ValidatedRefreshToken:
    record_id: UUID
    user_id: UUID

    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


@dataclass(frozen=True, slots=True)
class RotatedRefreshToken:
    revoked_record_id: UUID
    issued: IssuedRefreshToken


# ============================================================
# INTERNAL DATETIME HELPERS
# ============================================================


def _require_timezone_aware_datetime(
    value: datetime,
    *,
    field_name: str,
) -> datetime:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise RefreshTokenLifecycleError(
            f"{field_name} must be timezone-aware"
        )

    return value


def _normalize_database_datetime(
    value: datetime | None,
) -> datetime | None:
    if value is None:
        return None

    # SQLite test environments can return TIMESTAMPTZ values
    # without tzinfo. The database field represents an absolute
    # timestamp, so normalize that storage boundary to UTC.
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value


# ============================================================
# TOKEN LOOKUP
# ============================================================


async def _get_refresh_token_record(
    session: AsyncSession,
    *,
    token: str,
) -> RefreshToken:
    try:
        token_hash = hash_refresh_token(
            token
        )
    except RefreshTokenSecurityError as exc:
        raise RefreshTokenLifecycleError(
            str(exc)
        ) from exc

    result = await session.execute(
        select(RefreshToken)
        .where(
            RefreshToken.token_hash
            == token_hash
        )
        .limit(1)
    )

    record = result.scalars().first()

    if record is None:
        raise RefreshTokenLifecycleError(
            "Refresh token is invalid"
        )

    return record


# ============================================================
# ISSUE
# ============================================================


async def issue_refresh_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    issued_at: datetime | None = None,
) -> IssuedRefreshToken:
    user = await session.get(
        User,
        user_id,
    )

    if user is None:
        raise RefreshTokenLifecycleError(
            "User not found"
        )

    if not user.is_active:
        raise RefreshTokenLifecycleError(
            "User is inactive"
        )

    try:
        material = create_refresh_token_material(
            issued_at=issued_at,
        )
    except RefreshTokenSecurityError as exc:
        raise RefreshTokenLifecycleError(
            str(exc)
        ) from exc

    record = RefreshToken(
        user_id=user.id,
        token_hash=material.token_hash,
        issued_at=material.issued_at,
        expires_at=material.expires_at,
        revoked_at=None,
    )

    session.add(record)

    await session.commit()
    await session.refresh(record)

    return IssuedRefreshToken(
        token=material.token,
        record_id=record.id,
        user_id=record.user_id,
        issued_at=material.issued_at,
        expires_at=material.expires_at,
    )


# ============================================================
# VALIDATE
# ============================================================


async def validate_persisted_refresh_token(
    session: AsyncSession,
    *,
    token: str,
    current_time: datetime | None = None,
) -> ValidatedRefreshToken:
    evaluation_time = (
        current_time
        or datetime.now(timezone.utc)
    )

    _require_timezone_aware_datetime(
        evaluation_time,
        field_name="Current time",
    )

    record = await _get_refresh_token_record(
        session,
        token=token,
    )

    issued_at = _normalize_database_datetime(
        record.issued_at
    )

    expires_at = _normalize_database_datetime(
        record.expires_at
    )

    revoked_at = _normalize_database_datetime(
        record.revoked_at
    )

    assert issued_at is not None
    assert expires_at is not None

    if revoked_at is not None:
        raise RefreshTokenLifecycleError(
            "Refresh token has been revoked"
        )

    if evaluation_time >= expires_at:
        raise RefreshTokenLifecycleError(
            "Refresh token has expired"
        )

    if evaluation_time < issued_at:
        raise RefreshTokenLifecycleError(
            "Refresh token cannot be used before its issue time"
        )

    user = await session.get(
        User,
        record.user_id,
    )

    if user is None:
        raise RefreshTokenLifecycleError(
            "Refresh token user not found"
        )

    if not user.is_active:
        raise RefreshTokenLifecycleError(
            "Refresh token user is inactive"
        )

    return ValidatedRefreshToken(
        record_id=record.id,
        user_id=record.user_id,
        issued_at=issued_at,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


# ============================================================
# REVOKE
# ============================================================


async def revoke_refresh_token(
    session: AsyncSession,
    *,
    token: str,
    revoked_at: datetime | None = None,
) -> ValidatedRefreshToken:
    revocation_time = (
        revoked_at
        or datetime.now(timezone.utc)
    )

    _require_timezone_aware_datetime(
        revocation_time,
        field_name="Refresh token revocation time",
    )

    record = await _get_refresh_token_record(
        session,
        token=token,
    )

    issued_at = _normalize_database_datetime(
        record.issued_at
    )

    expires_at = _normalize_database_datetime(
        record.expires_at
    )

    existing_revoked_at = (
        _normalize_database_datetime(
            record.revoked_at
        )
    )

    assert issued_at is not None
    assert expires_at is not None

    if existing_revoked_at is not None:
        raise RefreshTokenLifecycleError(
            "Refresh token has already been revoked"
        )

    if revocation_time < issued_at:
        raise RefreshTokenLifecycleError(
            "Refresh token revocation time cannot be before issue time"
        )

    record.revoked_at = revocation_time

    await session.commit()
    await session.refresh(record)

    return ValidatedRefreshToken(
        record_id=record.id,
        user_id=record.user_id,
        issued_at=issued_at,
        expires_at=expires_at,
        revoked_at=revocation_time,
    )


# ============================================================
# ROTATE
# ============================================================


async def rotate_refresh_token(
    session: AsyncSession,
    *,
    token: str,
    current_time: datetime | None = None,
) -> RotatedRefreshToken:
    rotation_time = (
        current_time
        or datetime.now(timezone.utc)
    )

    _require_timezone_aware_datetime(
        rotation_time,
        field_name="Current time",
    )

    validated = (
        await validate_persisted_refresh_token(
            session,
            token=token,
            current_time=rotation_time,
        )
    )

    record = await session.get(
        RefreshToken,
        validated.record_id,
    )

    if record is None:
        raise RefreshTokenLifecycleError(
            "Refresh token is invalid"
        )

    # Revoke the old token first.
    record.revoked_at = rotation_time

    # Generate the replacement before committing so both
    # lifecycle changes are persisted in the same transaction.
    try:
        material = create_refresh_token_material(
            issued_at=rotation_time,
        )
    except RefreshTokenSecurityError as exc:
        raise RefreshTokenLifecycleError(
            str(exc)
        ) from exc

    replacement = RefreshToken(
        user_id=validated.user_id,
        token_hash=material.token_hash,
        issued_at=material.issued_at,
        expires_at=material.expires_at,
        revoked_at=None,
    )

    session.add(replacement)

    await session.commit()

    await session.refresh(record)
    await session.refresh(replacement)

    issued = IssuedRefreshToken(
        token=material.token,
        record_id=replacement.id,
        user_id=replacement.user_id,
        issued_at=material.issued_at,
        expires_at=material.expires_at,
    )

    return RotatedRefreshToken(
        revoked_record_id=record.id,
        issued=issued,
    )