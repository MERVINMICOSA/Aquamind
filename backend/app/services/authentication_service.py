from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UserRole
from app.models.system import User
from app.services.refresh_token_service import (
    IssuedRefreshToken,
    RefreshTokenLifecycleError,
    issue_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    validate_persisted_refresh_token,
)
from app.services.security_service import (
    AccessTokenError,
    PasswordSecurityError,
    create_access_token,
    verify_password,
)


# ============================================================
# EXCEPTIONS
# ============================================================


class AuthenticationError(ValueError):
    """Raised when user authentication cannot be completed."""


# ============================================================
# DATA OBJECTS
# ============================================================


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    user_id: UUID
    username: str
    role: UserRole

    access_token: str
    refresh_token: str

    refresh_token_record_id: UUID
    refresh_token_expires_at: datetime

    authenticated_at: datetime


# ============================================================
# INTERNAL VALIDATION
# ============================================================


def _validate_username(
    username: str,
) -> str:
    if not isinstance(username, str):
        raise AuthenticationError(
            "Username must be a string"
        )

    normalized = username.strip()

    if not normalized:
        raise AuthenticationError(
            "Username cannot be empty"
        )

    return normalized


def _validate_password(
    password: str,
) -> str:
    if not isinstance(password, str):
        raise AuthenticationError(
            "Password must be a string"
        )

    if not password:
        raise AuthenticationError(
            "Password cannot be empty"
        )

    return password


def _validate_authentication_time(
    value: datetime,
) -> datetime:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise AuthenticationError(
            "Authentication time must be timezone-aware"
        )

    return value


# ============================================================
# USER LOOKUP
# ============================================================


async def get_user_by_username(
    session: AsyncSession,
    *,
    username: str,
) -> User | None:
    normalized_username = (
        _validate_username(
            username
        )
    )

    result = await session.execute(
        select(User)
        .where(
            User.username
            == normalized_username
        )
        .limit(1)
    )

    return result.scalars().first()


# ============================================================
# CREDENTIAL VERIFICATION
# ============================================================


async def verify_user_credentials(
    session: AsyncSession,
    *,
    username: str,
    password: str,
) -> User:
    normalized_username = (
        _validate_username(
            username
        )
    )

    validated_password = (
        _validate_password(
            password
        )
    )

    user = await get_user_by_username(
        session,
        username=normalized_username,
    )

    if user is None:
        raise AuthenticationError(
            "Invalid username or password"
        )

    try:
        password_valid = verify_password(
            validated_password,
            user.password_hash,
        )
    except PasswordSecurityError as exc:
        raise AuthenticationError(
            "Invalid username or password"
        ) from exc

    if not password_valid:
        raise AuthenticationError(
            "Invalid username or password"
        )

    if not user.is_active:
        raise AuthenticationError(
            "User account is inactive"
        )

    return user


# ============================================================
# AUTHENTICATION
# ============================================================


async def authenticate_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    authenticated_at: datetime | None = None,
) -> AuthenticationResult:
    authentication_time = (
        authenticated_at
        or datetime.now(timezone.utc)
    )

    _validate_authentication_time(
        authentication_time
    )

    user = await verify_user_credentials(
        session,
        username=username,
        password=password,
    )

    try:
        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            issued_at=authentication_time,
        )
    except AccessTokenError as exc:
        raise AuthenticationError(
            "Access token could not be created"
        ) from exc

    # Mark the successful authentication timestamp before
    # issuing the refresh token. issue_refresh_token() commits
    # the current transaction, so last_login_at and the new
    # refresh-token record are persisted together.
    user.last_login_at = (
        authentication_time
    )

    try:
        issued_refresh_token: IssuedRefreshToken = (
            await issue_refresh_token(
                session,
                user_id=user.id,
                issued_at=authentication_time,
            )
        )

    except RefreshTokenLifecycleError as exc:
        await session.rollback()

        raise AuthenticationError(
            "Refresh token could not be issued"
        ) from exc

    return AuthenticationResult(
        user_id=user.id,
        username=user.username,
        role=user.role,
        access_token=access_token,
        refresh_token=issued_refresh_token.token,
        refresh_token_record_id=(
            issued_refresh_token.record_id
        ),
        refresh_token_expires_at=(
            issued_refresh_token.expires_at
        ),
        authenticated_at=authentication_time,
    )


# ============================================================
# REFRESH AUTHENTICATION
# ============================================================


async def refresh_authentication(
    session: AsyncSession,
    *,
    refresh_token: str,
    refreshed_at: datetime | None = None,
) -> AuthenticationResult:
    refresh_time = (
        refreshed_at
        or datetime.now(timezone.utc)
    )

    _validate_authentication_time(
        refresh_time
    )

    try:
        validated = (
            await validate_persisted_refresh_token(
                session,
                token=refresh_token,
                current_time=refresh_time,
            )
        )
    except RefreshTokenLifecycleError as exc:
        raise AuthenticationError(
            "Refresh token is invalid"
        ) from exc

    user = await session.get(
        User,
        validated.user_id,
    )

    if user is None:
        raise AuthenticationError(
            "Refresh token is invalid"
        )

    if not user.is_active:
        raise AuthenticationError(
            "Refresh token is invalid"
        )

    # Create the new access token before rotating the
    # refresh token. If access-token creation fails,
    # the existing refresh token remains usable.
    try:
        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            issued_at=refresh_time,
        )
    except AccessTokenError as exc:
        raise AuthenticationError(
            "Access token could not be created"
        ) from exc

    try:
        rotated = await rotate_refresh_token(
            session,
            token=refresh_token,
            current_time=refresh_time,
        )
    except RefreshTokenLifecycleError as exc:
        raise AuthenticationError(
            "Refresh token could not be rotated"
        ) from exc

    return AuthenticationResult(
        user_id=user.id,
        username=user.username,
        role=user.role,
        access_token=access_token,
        refresh_token=rotated.issued.token,
        refresh_token_record_id=(
            rotated.issued.record_id
        ),
        refresh_token_expires_at=(
            rotated.issued.expires_at
        ),
        authenticated_at=refresh_time,
    )


# ============================================================
# LOGOUT
# ============================================================


async def logout_user(
    session: AsyncSession,
    *,
    refresh_token: str,
    logged_out_at: datetime | None = None,
) -> UUID:
    logout_time = (
        logged_out_at
        or datetime.now(timezone.utc)
    )

    _validate_authentication_time(
        logout_time
    )

    try:
        revoked = await revoke_refresh_token(
            session,
            token=refresh_token,
            revoked_at=logout_time,
        )
    except RefreshTokenLifecycleError as exc:
        raise AuthenticationError(
            "Refresh token could not be revoked"
        ) from exc

    return revoked.user_id