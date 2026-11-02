from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.core.config import settings
from app.db.enums import UserRole
from app.services.security_service import (
    AccessTokenClaims,
    AccessTokenError,
    create_access_token,
    decode_access_token,
)


TEST_SECRET = (
    "aquamind-test-secret-key-"
    "0123456789abcdef-"
    "0123456789abcdef-"
    "0123456789abcdef"
)


@pytest.fixture(autouse=True)
def configure_test_jwt(monkeypatch):
    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        TEST_SECRET,
    )

    monkeypatch.setattr(
        settings,
        "JWT_ALGORITHM",
        "HS256",
    )

    monkeypatch.setattr(
        settings,
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        30,
    )

    monkeypatch.setattr(
        settings,
        "JWT_ISSUER",
        "aquamind",
    )

    monkeypatch.setattr(
        settings,
        "JWT_AUDIENCE",
        "aquamind-api",
    )


# ============================================================
# CREATION
# ============================================================


def test_create_and_decode_access_token():
    user_id = uuid4()

    token = create_access_token(
        user_id=user_id,
        role=UserRole.ADMIN,
    )

    claims = decode_access_token(
        token
    )

    assert isinstance(
        claims,
        AccessTokenClaims,
    )

    assert claims.user_id == user_id

    assert (
        claims.role
        == UserRole.ADMIN
    )

    assert (
        claims.expires_at
        > claims.issued_at
    )


def test_access_token_contains_expected_claims():
    user_id = uuid4()

    token = create_access_token(
        user_id=user_id,
        role=UserRole.ADMIN,
    )

    payload = jwt.decode(
        token,
        TEST_SECRET,
        algorithms=["HS256"],
        issuer="aquamind",
        audience="aquamind-api",
    )

    assert payload["sub"] == str(
        user_id
    )

    assert payload["role"] == "admin"

    assert "iat" in payload
    assert "exp" in payload
    assert "jti" in payload

    assert payload["iss"] == "aquamind"

    assert (
        payload["aud"]
        == "aquamind-api"
    )


def test_access_token_uses_configured_lifetime():
    issued_at = datetime.now(
        timezone.utc
    )

    token = create_access_token(
        user_id=uuid4(),
        role=UserRole.ADMIN,
        issued_at=issued_at,
    )

    claims = decode_access_token(
        token
    )

    lifetime = (
        claims.expires_at
        - claims.issued_at
    )

    assert lifetime == timedelta(
        minutes=30
    )


def test_each_access_token_has_unique_jti():
    user_id = uuid4()

    first = decode_access_token(
        create_access_token(
            user_id=user_id,
            role=UserRole.ADMIN,
        )
    )

    second = decode_access_token(
        create_access_token(
            user_id=user_id,
            role=UserRole.ADMIN,
        )
    )

    assert (
        first.token_id
        != second.token_id
    )


# ============================================================
# CONFIGURATION VALIDATION
# ============================================================


def test_missing_jwt_secret_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        "",
    )

    with pytest.raises(
        AccessTokenError,
        match=(
            "JWT secret key is not configured"
        ),
    ):
        create_access_token(
            user_id=uuid4(),
            role=UserRole.ADMIN,
        )


def test_short_jwt_secret_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        "too-short",
    )

    with pytest.raises(
        AccessTokenError,
        match=(
            "JWT secret key must be "
            "at least 64 characters"
        ),
    ):
        create_access_token(
            user_id=uuid4(),
            role=UserRole.ADMIN,
        )


def test_unsupported_algorithm_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "JWT_ALGORITHM",
        "HS512",
    )

    with pytest.raises(
        AccessTokenError,
        match="Unsupported JWT algorithm",
    ):
        create_access_token(
            user_id=uuid4(),
            role=UserRole.ADMIN,
        )


def test_invalid_access_token_lifetime_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        0,
    )

    with pytest.raises(
        AccessTokenError,
        match=(
            "Access token lifetime must "
            "be greater than zero"
        ),
    ):
        create_access_token(
            user_id=uuid4(),
            role=UserRole.ADMIN,
        )


def test_naive_issue_time_is_rejected():
    issued_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
    )

    with pytest.raises(
        AccessTokenError,
        match=(
            "Access token issue time "
            "must be timezone-aware"
        ),
    ):
        create_access_token(
            user_id=uuid4(),
            role=UserRole.ADMIN,
            issued_at=issued_at,
        )


# ============================================================
# TOKEN VALIDATION
# ============================================================


def test_empty_access_token_is_rejected():
    with pytest.raises(
        AccessTokenError,
        match="Access token cannot be empty",
    ):
        decode_access_token("")


def test_malformed_access_token_is_rejected():
    with pytest.raises(
        AccessTokenError,
        match="Access token is invalid",
    ):
        decode_access_token(
            "not-a-jwt"
        )


def test_token_signed_with_wrong_secret_is_rejected():
    now = datetime.now(
        timezone.utc
    )

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "admin",
            "iat": now,
            "exp": (
                now
                + timedelta(minutes=30)
            ),
            "jti": str(uuid4()),
            "iss": "aquamind",
            "aud": "aquamind-api",
        },
        (
            "wrong-secret-"
            "0123456789abcdef"
            "0123456789abcdef"
            "0123456789abcdef"
            "0123456789abcdef"
        ),
        algorithm="HS256",
    )

    with pytest.raises(
        AccessTokenError,
        match="Access token is invalid",
    ):
        decode_access_token(
            token
        )


def test_expired_access_token_is_rejected():
    now = datetime.now(
        timezone.utc
    )

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "admin",
            "iat": (
                now
                - timedelta(minutes=60)
            ),
            "exp": (
                now
                - timedelta(minutes=30)
            ),
            "jti": str(uuid4()),
            "iss": "aquamind",
            "aud": "aquamind-api",
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(
        AccessTokenError,
        match="Access token has expired",
    ):
        decode_access_token(
            token
        )


def test_invalid_role_claim_is_rejected():
    now = datetime.now(
        timezone.utc
    )

    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "superuser",
            "iat": now,
            "exp": (
                now
                + timedelta(minutes=30)
            ),
            "jti": str(uuid4()),
            "iss": "aquamind",
            "aud": "aquamind-api",
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(
        AccessTokenError,
        match=(
            "Access token claims are invalid"
        ),
    ):
        decode_access_token(
            token
        )


def test_invalid_user_id_claim_is_rejected():
    now = datetime.now(
        timezone.utc
    )

    token = jwt.encode(
        {
            "sub": "not-a-uuid",
            "role": "admin",
            "iat": now,
            "exp": (
                now
                + timedelta(minutes=30)
            ),
            "jti": str(uuid4()),
            "iss": "aquamind",
            "aud": "aquamind-api",
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(
        AccessTokenError,
        match=(
            "Access token claims are invalid"
        ),
    ):
        decode_access_token(
            token
        )