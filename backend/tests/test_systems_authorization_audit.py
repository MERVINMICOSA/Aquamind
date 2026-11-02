from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select

from app.api.dependencies import (
    get_current_user,
)
from app.db.enums import UserRole
from app.main import app
from app.models.other import AuditLog
from app.models.system import User


pytestmark = pytest.mark.asyncio


async def create_admin(
    session,
):
    user = User(
        username="systems-audit-admin",
        password_hash="test-password-hash",
        role=UserRole.ADMIN,
        is_active=True,
    )

    session.add(user)

    await session.commit()
    await session.refresh(user)

    return user


async def use_current_user(
    user,
):
    async def override_get_current_user():
        return user

    app.dependency_overrides[
        get_current_user
    ] = override_get_current_user


async def test_admin_create_system_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Audit System",
            "description": (
                "Created during audit test"
            ),
            "timezone": "Asia/Manila",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system = response.json()

    system_id = UUID(
        system["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == system_id
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "create"
    assert audit.entity_type == "system"
    assert audit.entity_id == system_id
    assert audit.source == "api"

    assert audit.old_value is None

    assert audit.new_value == {
        "name": "Audit System",
        "description": (
            "Created during audit test"
        ),
        "timezone": "Asia/Manila",
        "is_active": True,
    }


async def test_admin_update_system_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    create_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Original System",
            "description": None,
            "timezone": "Asia/Manila",
            "is_active": True,
        },
    )

    assert (
        create_response.status_code
        == 201
    )

    system_id = UUID(
        create_response.json()["id"]
    )

    update_response = await client.patch(
        f"/api/v1/systems/{system_id}",
        json={
            "name": "Updated System",
            "is_active": False,
        },
    )

    assert (
        update_response.status_code
        == 200
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == system_id
        )
        .where(
            AuditLog.action
            == "update"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "update"
    assert audit.entity_type == "system"
    assert audit.entity_id == system_id
    assert audit.source == "api"

    assert audit.old_value == {
        "name": "Original System",
        "is_active": True,
    }

    assert audit.new_value == {
        "name": "Updated System",
        "is_active": False,
    }


async def test_non_admin_cannot_create_system(
    client,
):
    non_admin = SimpleNamespace(
        role="non-admin",
    )

    await use_current_user(
        non_admin
    )

    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Forbidden System",
            "description": None,
            "timezone": "Asia/Manila",
            "is_active": True,
        },
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }