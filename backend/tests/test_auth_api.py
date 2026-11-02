from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from app.api.dependencies import (
    get_db_session,
)
from app.core.config import settings
from app.db.enums import UserRole
from app.main import app
from app.models.system import User
from app.services.security_service import (
    hash_password,
)


pytestmark = pytest.mark.asyncio


TEST_SECRET = (
    "aquamind-auth-api-test-secret-"
    "0123456789abcdef-"
    "0123456789abcdef-"
    "0123456789abcdef"
)


# ============================================================
# FIXTURES
# ============================================================


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


@pytest_asyncio.fixture
async def auth_client(
    test_session,
):
    async def override_get_db_session():
        yield test_session

    app.dependency_overrides[
        get_db_session
    ] = override_get_db_session

    transport = httpx.ASGITransport(
        app=app
    )

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.pop(
        get_db_session,
        None,
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
# LOGIN
# ============================================================


async def test_login_returns_token_pair(
    test_session,
    auth_client,
):
    user = await create_user(
        test_session
    )

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": (
                "AquaMindAdmin123!"
            ),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["user_id"] == str(
        user.id
    )

    assert body["username"] == "admin"
    assert body["role"] == "admin"

    assert body["access_token"]
    assert body["refresh_token"]

    assert (
        body["token_type"]
        == "bearer"
    )

    assert (
        body["refresh_token_expires_at"]
    )


async def test_login_rejects_wrong_password(
    test_session,
    auth_client,
):
    await create_user(
        test_session
    )

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": (
            "Invalid username or password"
        )
    }


# ============================================================
# REFRESH
# ============================================================


async def test_refresh_rotates_token_pair(
    test_session,
    auth_client,
):
    await create_user(
        test_session
    )

    login_response = (
        await auth_client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": (
                    "AquaMindAdmin123!"
                ),
            },
        )
    )

    assert (
        login_response.status_code
        == 200
    )

    original = login_response.json()

    refresh_response = (
        await auth_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": (
                    original[
                        "refresh_token"
                    ]
                )
            },
        )
    )

    assert (
        refresh_response.status_code
        == 200
    )

    refreshed = refresh_response.json()

    assert refreshed["access_token"]

    assert (
        refreshed["refresh_token"]
        != original["refresh_token"]
    )

    assert (
        refreshed["user_id"]
        == original["user_id"]
    )


async def test_rotated_refresh_token_cannot_be_reused(
    test_session,
    auth_client,
):
    await create_user(
        test_session
    )

    login_response = (
        await auth_client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": (
                    "AquaMindAdmin123!"
                ),
            },
        )
    )

    original_token = (
        login_response.json()[
            "refresh_token"
        ]
    )

    first_refresh = (
        await auth_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": (
                    original_token
                )
            },
        )
    )

    assert first_refresh.status_code == 200

    reuse_response = (
        await auth_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": (
                    original_token
                )
            },
        )
    )

    assert (
        reuse_response.status_code
        == 401
    )

    assert reuse_response.json() == {
        "detail": "Invalid refresh token"
    }


# ============================================================
# LOGOUT
# ============================================================


async def test_logout_revokes_refresh_token(
    test_session,
    auth_client,
):
    await create_user(
        test_session
    )

    login_response = (
        await auth_client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": (
                    "AquaMindAdmin123!"
                ),
            },
        )
    )

    refresh_token = (
        login_response.json()[
            "refresh_token"
        ]
    )

    logout_response = (
        await auth_client.post(
            "/api/v1/auth/logout",
            json={
                "refresh_token": (
                    refresh_token
                )
            },
        )
    )

    assert (
        logout_response.status_code
        == 204
    )

    refresh_response = (
        await auth_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": (
                    refresh_token
                )
            },
        )
    )

    assert (
        refresh_response.status_code
        == 401
    )


async def test_logout_is_idempotent(
    test_session,
    auth_client,
):
    await create_user(
        test_session
    )

    login_response = (
        await auth_client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": (
                    "AquaMindAdmin123!"
                ),
            },
        )
    )

    refresh_token = (
        login_response.json()[
            "refresh_token"
        ]
    )

    first = await auth_client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token
        },
    )

    second = await auth_client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token
        },
    )

    assert first.status_code == 204
    assert second.status_code == 204