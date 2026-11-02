from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.db.enums import UserRole
from app.models.system import RefreshToken, User
from app.services.authentication_service import (
    AuthenticationError,
    AuthenticationResult,
    authenticate_user,
    get_user_by_username,
    verify_user_credentials,
)
from app.services.security_service import (
    decode_access_token,
    hash_password,
    hash_refresh_token,
)


pytestmark = pytest.mark.asyncio


TEST_SECRET = (
    "aquamind-authentication-test-secret-"
    "0123456789abcdef-"
    "0123456789abcdef-"
    "0123456789abcdef"
)


@pytest.fixture(autouse=True)
def configure_auth_settings(
    monkeypatch,
):
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
        "REFRESH_TOKEN_EXPIRE_DAYS",
        7,
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
# HELPERS
# ============================================================


async def create_user(
    session,
    *,
    username="admin",
    password="AquaMindAdmin123!",
    is_active=True,
):
    user = User(
        username=username,
        password_hash=hash_password(
            password
        ),
        role=UserRole.ADMIN,
        is_active=is_active,
    )

    session.add(user)

    await session.commit()
    await session.refresh(user)

    return user


# ============================================================
# USER LOOKUP
# ============================================================


async def test_get_user_by_username(
    test_session,
):
    user = await create_user(
        test_session
    )

    result = await get_user_by_username(
        test_session,
        username="admin",
    )

    assert result is not None
    assert result.id == user.id


async def test_get_user_by_username_returns_none_when_missing(
    test_session,
):
    result = await get_user_by_username(
        test_session,
        username="missing-user",
    )

    assert result is None


# ============================================================
# CREDENTIAL VERIFICATION
# ============================================================


async def test_valid_credentials_return_user(
    test_session,
):
    user = await create_user(
        test_session
    )

    result = await verify_user_credentials(
        test_session,
        username="admin",
        password="AquaMindAdmin123!",
    )

    assert result.id == user.id


async def test_unknown_username_is_rejected(
    test_session,
):
    with pytest.raises(
        AuthenticationError,
        match="Invalid username or password",
    ):
        await verify_user_credentials(
            test_session,
            username="missing-user",
            password="AquaMindAdmin123!",
        )


async def test_wrong_password_is_rejected(
    test_session,
):
    await create_user(
        test_session
    )

    with pytest.raises(
        AuthenticationError,
        match="Invalid username or password",
    ):
        await verify_user_credentials(
            test_session,
            username="admin",
            password="WrongPassword123!",
        )


async def test_inactive_user_is_rejected(
    test_session,
):
    await create_user(
        test_session,
        is_active=False,
    )

    with pytest.raises(
        AuthenticationError,
        match="User account is inactive",
    ):
        await verify_user_credentials(
            test_session,
            username="admin",
            password="AquaMindAdmin123!",
        )


# ============================================================
# COMPLETE AUTHENTICATION
# ============================================================


async def test_authenticate_user_returns_token_pair(
    test_session,
):
    user = await create_user(
        test_session
    )

    authentication_time = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    result = await authenticate_user(
        test_session,
        username="admin",
        password="AquaMindAdmin123!",
        authenticated_at=authentication_time,
    )

    assert isinstance(
        result,
        AuthenticationResult,
    )

    assert result.user_id == user.id
    assert result.username == "admin"

    assert (
        result.role
        == UserRole.ADMIN
    )

    assert result.access_token
    assert result.refresh_token

    assert (
        result.authenticated_at
        == authentication_time
    )


async def test_authenticate_user_access_token_matches_user(
    test_session,
):
    user = await create_user(
        test_session
    )

    result = await authenticate_user(
        test_session,
        username="admin",
        password="AquaMindAdmin123!",
    )

    claims = decode_access_token(
        result.access_token
    )

    assert claims.user_id == user.id

    assert (
        claims.role
        == UserRole.ADMIN
    )


async def test_authenticate_user_persists_only_refresh_token_hash(
    test_session,
):
    await create_user(
        test_session
    )

    result = await authenticate_user(
        test_session,
        username="admin",
        password="AquaMindAdmin123!",
    )

    record = await test_session.get(
        RefreshToken,
        result.refresh_token_record_id,
    )

    assert record is not None

    assert (
        record.token_hash
        == hash_refresh_token(
            result.refresh_token
        )
    )

    assert (
        record.token_hash
        != result.refresh_token
    )


async def test_authenticate_user_updates_last_login(
    test_session,
):
    user = await create_user(
        test_session
    )

    authentication_time = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    await authenticate_user(
        test_session,
        username="admin",
        password="AquaMindAdmin123!",
        authenticated_at=authentication_time,
    )

    await test_session.refresh(user)

    stored_last_login = (
        user.last_login_at
    )

    assert stored_last_login is not None

    # SQLite can strip timezone information from
    # TIMESTAMPTZ during tests.
    if stored_last_login.tzinfo is None:
        stored_last_login = (
            stored_last_login.replace(
                tzinfo=timezone.utc
            )
        )

    assert (
        stored_last_login
        == authentication_time
    )


async def test_naive_authentication_time_is_rejected(
    test_session,
):
    await create_user(
        test_session
    )

    with pytest.raises(
        AuthenticationError,
        match=(
            "Authentication time must "
            "be timezone-aware"
        ),
    ):
        await authenticate_user(
            test_session,
            username="admin",
            password="AquaMindAdmin123!",
            authenticated_at=datetime(
                2026,
                1,
                1,
                12,
                0,
                0,
            ),
        )