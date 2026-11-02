from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from uuid import UUID, uuid4

import bcrypt
import jwt

from app.core.config import settings
from app.db.enums import UserRole


# ============================================================
# PASSWORD CONFIGURATION
# ============================================================


BCRYPT_ROUNDS = 12
BCRYPT_MAX_PASSWORD_BYTES = 72
REFRESH_TOKEN_ENTROPY_BYTES = 64


# ============================================================
# EXCEPTIONS
# ============================================================


class PasswordSecurityError(ValueError):
    """Raised when password hashing input is invalid."""


class AccessTokenError(ValueError):
    """Raised when an access token cannot be created or validated."""


class RefreshTokenSecurityError(ValueError):
    """Raised when refresh-token security input is invalid."""

# ============================================================
# ACCESS TOKEN DATA
# ============================================================


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: UUID
    role: UserRole

    issued_at: datetime
    expires_at: datetime

    token_id: UUID

@dataclass(frozen=True, slots=True)
class RefreshTokenMaterial:
    token: str
    token_hash: str

    issued_at: datetime
    expires_at: datetime


# ============================================================
# PASSWORD VALIDATION
# ============================================================


def _validate_plain_password(
    password: str,
) -> bytes:
    if not isinstance(password, str):
        raise PasswordSecurityError(
            "Password must be a string"
        )

    if not password:
        raise PasswordSecurityError(
            "Password cannot be empty"
        )

    password_bytes = password.encode(
        "utf-8"
    )

    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        raise PasswordSecurityError(
            "Password exceeds bcrypt maximum length"
        )

    return password_bytes


# ============================================================
# PASSWORD HASHING
# ============================================================


def hash_password(
    password: str,
) -> str:
    password_bytes = _validate_plain_password(
        password
    )

    salt = bcrypt.gensalt(
        rounds=BCRYPT_ROUNDS
    )

    hashed = bcrypt.hashpw(
        password_bytes,
        salt,
    )

    return hashed.decode(
        "utf-8"
    )


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    password_bytes = _validate_plain_password(
        password
    )

    if not isinstance(
        password_hash,
        str,
    ):
        raise PasswordSecurityError(
            "Password hash must be a string"
        )

    if not password_hash:
        raise PasswordSecurityError(
            "Password hash cannot be empty"
        )

    try:
        return bcrypt.checkpw(
            password_bytes,
            password_hash.encode(
                "utf-8"
            ),
        )
    except (ValueError, TypeError):
        return False


# ============================================================
# JWT CONFIGURATION VALIDATION
# ============================================================


def _get_jwt_secret_key() -> str:
    secret_key = settings.JWT_SECRET_KEY

    if not secret_key:
        raise AccessTokenError(
            "JWT secret key is not configured"
        )

    if len(secret_key) < 64:
        raise AccessTokenError(
            "JWT secret key must be at least 64 characters"
        )

    return secret_key


def _validate_jwt_algorithm() -> str:
    algorithm = settings.JWT_ALGORITHM

    if algorithm != "HS256":
        raise AccessTokenError(
            "Unsupported JWT algorithm"
        )

    return algorithm


def _validate_access_token_lifetime() -> int:
    lifetime_minutes = (
        settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    if lifetime_minutes <= 0:
        raise AccessTokenError(
            "Access token lifetime must be greater than zero"
        )

    return lifetime_minutes


def _require_timezone_aware_datetime(
    value: datetime,
    *,
    field_name: str,
) -> datetime:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise AccessTokenError(
            f"{field_name} must be timezone-aware"
        )

    return value


# ============================================================
# ACCESS TOKEN CREATION
# ============================================================


def create_access_token(
    *,
    user_id: UUID,
    role: UserRole,
    issued_at: datetime | None = None,
) -> str:
    secret_key = _get_jwt_secret_key()
    algorithm = _validate_jwt_algorithm()

    lifetime_minutes = (
        _validate_access_token_lifetime()
    )

    issued_time = (
        issued_at
        or datetime.now(timezone.utc)
    )

    _require_timezone_aware_datetime(
        issued_time,
        field_name="Access token issue time",
    )

    expires_at = (
        issued_time
        + timedelta(
            minutes=lifetime_minutes
        )
    )

    token_id = uuid4()

    payload = {
        "sub": str(user_id),
        "role": role.value,
        "iat": issued_time,
        "exp": expires_at,
        "jti": str(token_id),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm,
    )


# ============================================================
# ACCESS TOKEN VALIDATION
# ============================================================


def decode_access_token(
    token: str,
) -> AccessTokenClaims:
    if not isinstance(token, str):
        raise AccessTokenError(
            "Access token must be a string"
        )

    if not token:
        raise AccessTokenError(
            "Access token cannot be empty"
        )

    secret_key = _get_jwt_secret_key()
    algorithm = _validate_jwt_algorithm()

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "require": [
                    "sub",
                    "role",
                    "iat",
                    "exp",
                    "jti",
                    "iss",
                    "aud",
                ]
            },
        )

    except jwt.ExpiredSignatureError as exc:
        raise AccessTokenError(
            "Access token has expired"
        ) from exc

    except jwt.InvalidTokenError as exc:
        raise AccessTokenError(
            "Access token is invalid"
        ) from exc

    try:
        user_id = UUID(
            payload["sub"]
        )

        role = UserRole(
            payload["role"]
        )

        token_id = UUID(
            payload["jti"]
        )

        issued_at = datetime.fromtimestamp(
            payload["iat"],
            tz=timezone.utc,
        )

        expires_at = datetime.fromtimestamp(
            payload["exp"],
            tz=timezone.utc,
        )

    except (
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        OSError,
    ) as exc:
        raise AccessTokenError(
            "Access token claims are invalid"
        ) from exc

    if expires_at <= issued_at:
        raise AccessTokenError(
            "Access token expiration must be after issue time"
        )

    return AccessTokenClaims(
        user_id=user_id,
        role=role,
        issued_at=issued_at,
        expires_at=expires_at,
        token_id=token_id,
    )


# ============================================================
# REFRESH TOKEN CONFIGURATION
# ============================================================


def _validate_refresh_token_lifetime() -> int:
    lifetime_days = (
        settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    if lifetime_days <= 0:
        raise RefreshTokenSecurityError(
            "Refresh token lifetime must be greater than zero"
        )

    return lifetime_days


def _validate_refresh_token_string(
    token: str,
) -> str:
    if not isinstance(token, str):
        raise RefreshTokenSecurityError(
            "Refresh token must be a string"
        )

    if not token:
        raise RefreshTokenSecurityError(
            "Refresh token cannot be empty"
        )

    return token


# ============================================================
# REFRESH TOKEN GENERATION
# ============================================================


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(
        REFRESH_TOKEN_ENTROPY_BYTES
    )


# ============================================================
# REFRESH TOKEN HASHING
# ============================================================


def hash_refresh_token(
    token: str,
) -> str:
    validated_token = (
        _validate_refresh_token_string(
            token
        )
    )

    return hashlib.sha256(
        validated_token.encode("utf-8")
    ).hexdigest()


def verify_refresh_token_hash(
    token: str,
    token_hash: str,
) -> bool:
    validated_token = (
        _validate_refresh_token_string(
            token
        )
    )

    if not isinstance(token_hash, str):
        raise RefreshTokenSecurityError(
            "Refresh token hash must be a string"
        )

    if not token_hash:
        raise RefreshTokenSecurityError(
            "Refresh token hash cannot be empty"
        )

    calculated_hash = hash_refresh_token(
        validated_token
    )

    return hmac.compare_digest(
        calculated_hash,
        token_hash,
    )


# ============================================================
# REFRESH TOKEN MATERIAL
# ============================================================


def create_refresh_token_material(
    *,
    issued_at: datetime | None = None,
) -> RefreshTokenMaterial:
    lifetime_days = (
        _validate_refresh_token_lifetime()
    )

    issue_time = (
        issued_at
        or datetime.now(timezone.utc)
    )

    if (
        issue_time.tzinfo is None
        or issue_time.utcoffset() is None
    ):
        raise RefreshTokenSecurityError(
            "Refresh token issue time must be timezone-aware"
        )

    expires_at = (
        issue_time
        + timedelta(
            days=lifetime_days
        )
    )

    token = generate_refresh_token()

    token_hash = hash_refresh_token(
        token
    )

    return RefreshTokenMaterial(
        token=token,
        token_hash=token_hash,
        issued_at=issue_time,
        expires_at=expires_at,
    )