from __future__ import annotations

from uuid import uuid4

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
    create_access_token,
    hash_password,
)


pytestmark = pytest.mark.asyncio


TEST_SECRET = (
    "aquamind-current-user-test-secret-"
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


async def create_user(
    session,
    *,
    username="admin",
    is_active=True,
):
    user = User(
        username=username,
        password_hash=hash_password(
            "AquaMindAdmin123!"
        ),
        role=UserRole.ADMIN,
        is_active=is_active,
    )

    session.add(user)

    await session.commit()
    await session.refresh(user)

    return user


async def test_current_user_returns_authenticated_user(
    test_session,
    auth_client,
):
    user = await create_user(
        test_session
    )

    token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": (
                f"Bearer {token}"
            )
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "user_id": str(user.id),
        "username": "admin",
        "role": "admin",
        "is_active": True,
    }


async def test_current_user_requires_authorization_header(
    auth_client,
):
    response = await auth_client.get(
        "/api/v1/auth/me"
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": "Authentication required"
    }

    assert (
        response.headers[
            "www-authenticate"
        ]
        == "Bearer"
    )


async def test_current_user_rejects_invalid_access_token(
    auth_client,
):
    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": (
                "Bearer not-a-valid-token"
            )
        },
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": "Authentication required"
    }


async def test_current_user_rejects_unknown_user(
    auth_client,
):
    token = create_access_token(
        user_id=uuid4(),
        role=UserRole.ADMIN,
    )

    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": (
                f"Bearer {token}"
            )
        },
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": "Authentication required"
    }


async def test_current_user_rejects_inactive_user(
    test_session,
    auth_client,
):
    user = await create_user(
        test_session
    )

    token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    user.is_active = False

    await test_session.commit()

    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": (
                f"Bearer {token}"
            )
        },
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": "Authentication required"
    }