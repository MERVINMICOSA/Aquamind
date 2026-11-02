from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.api.dependencies import (
    get_db_session,
)
from app.core.config import settings
from app.db.enums import UserRole
from app.main import app
from app.models.other import AuditLog
from app.models.system import User
from app.services.security_service import (
    hash_password,
)


pytestmark = pytest.mark.asyncio


TEST_SECRET = (
    "aquamind-auth-audit-test-secret-"
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
):
    user = User(
        username="auth-audit-admin",
        password_hash=hash_password(
            "AquaMindAdmin123!"
        ),
        role=UserRole.ADMIN,
        is_active=True,
    )

    session.add(user)

    await session.commit()
    await session.refresh(user)

    return user


async def login_user(
    auth_client,
):
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "username": "auth-audit-admin",
            "password": (
                "AquaMindAdmin123!"
            ),
        },
    )

    assert response.status_code == 200

    return response.json()


# ============================================================
# LOGIN AUDIT
# ============================================================


async def test_successful_login_creates_login_audit(
    test_session,
    auth_client,
):
    user = await create_user(
        test_session
    )

    await login_user(
        auth_client
    )

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.user_id == user.id,
            AuditLog.action == "login",
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == user.id
    assert audit.action == "login"
    assert audit.entity_type == "user"
    assert audit.entity_id == user.id
    assert audit.source == "api"
    assert audit.old_value is None
    assert audit.new_value is None


async def test_failed_login_does_not_create_login_audit(
    test_session,
    auth_client,
):
    user = await create_user(
        test_session
    )

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "username": "auth-audit-admin",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.user_id == user.id,
            AuditLog.action == "login",
        )
    )

    assert result.scalars().all() == []


# ============================================================
# REFRESH AUDIT
# ============================================================


async def test_successful_refresh_creates_refresh_audit(
    test_session,
    auth_client,
):
    user = await create_user(
        test_session
    )

    login = await login_user(
        auth_client
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": (
                login["refresh_token"]
            )
        },
    )

    assert response.status_code == 200

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.user_id == user.id,
            AuditLog.action == "refresh",
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == user.id
    assert audit.action == "refresh"
    assert audit.entity_type == "user"
    assert audit.entity_id == user.id
    assert audit.source == "api"


async def test_failed_refresh_does_not_create_refresh_audit(
    test_session,
    auth_client,
):
    user = await create_user(
        test_session
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": (
                "invalid-refresh-token"
            )
        },
    )

    assert response.status_code == 401

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.user_id == user.id,
            AuditLog.action == "refresh",
        )
    )

    assert result.scalars().all() == []


# ============================================================
# LOGOUT AUDIT
# ============================================================


async def test_successful_logout_creates_one_logout_audit_and_retry_does_not(
    test_session,
    auth_client,
):
    user = await create_user(
        test_session
    )

    login = await login_user(
        auth_client
    )

    refresh_token = (
        login["refresh_token"]
    )

    first = await auth_client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token
        },
    )

    assert first.status_code == 204

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.user_id == user.id,
            AuditLog.action == "logout",
        )
    )

    audits = result.scalars().all()

    assert len(audits) == 1

    audit = audits[0]

    assert audit.user_id == user.id
    assert audit.action == "logout"
    assert audit.entity_type == "user"
    assert audit.entity_id == user.id
    assert audit.source == "api"

    # Same token is already revoked. HTTP logout remains
    # idempotent, and no false second logout event is written.
    second = await auth_client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token
        },
    )

    assert second.status_code == 204

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.user_id == user.id,
            AuditLog.action == "logout",
        )
    )

    assert len(
        result.scalars().all()
    ) == 1