from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.api.dependencies import (
    get_current_user,
    require_admin,
)
from app.api.grow_beds import router
from app.db.enums import UserRole
from app.main import app
from app.models.other import AuditLog
from app.models.system import (
    AquaponicsSystem,
    User,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# HELPERS
# ============================================================


async def create_admin(
    session,
):
    user = User(
        username="grow-beds-audit-admin",
        password_hash="test-password-hash",
        role=UserRole.ADMIN,
        is_active=True,
    )

    session.add(user)

    await session.commit()
    await session.refresh(user)

    return user


async def create_system(
    session,
):
    system = AquaponicsSystem(
        name="Grow Bed Audit System",
        description=None,
        timezone="Asia/Manila",
        is_active=True,
    )

    session.add(system)

    await session.commit()
    await session.refresh(system)

    return system


async def use_current_user(
    user,
):
    async def override_get_current_user():
        return user

    app.dependency_overrides[
        get_current_user
    ] = override_get_current_user


# ============================================================
# CREATE
# ============================================================


async def test_admin_create_grow_bed_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    system = await create_system(
        test_session
    )

    await use_current_user(
        admin
    )

    response = await client.post(
        "/api/v1/grow-beds",
        json={
            "system_id": str(
                system.id
            ),
            "name": "Audit Grow Bed",
            "crop_type": "Lettuce",
            "capacity_description": (
                "20 plant sites"
            ),
            "is_active": True,
        },
    )

    assert response.status_code == 201

    grow_bed = response.json()

    grow_bed_id = UUID(
        grow_bed["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == grow_bed_id
        )
        .where(
            AuditLog.action
            == "create"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "create"
    assert audit.entity_type == "grow_bed"
    assert audit.entity_id == grow_bed_id
    assert audit.source == "api"

    assert audit.old_value is None

    assert audit.new_value == {
        "system_id": str(system.id),
        "name": "Audit Grow Bed",
        "crop_type": "Lettuce",
        "capacity_description": (
            "20 plant sites"
        ),
        "is_active": True,
    }


# ============================================================
# UPDATE
# ============================================================


async def test_admin_update_grow_bed_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    system = await create_system(
        test_session
    )

    await use_current_user(
        admin
    )

    create_response = await client.post(
        "/api/v1/grow-beds",
        json={
            "system_id": str(
                system.id
            ),
            "name": "Original Grow Bed",
            "crop_type": "Lettuce",
            "capacity_description": (
                "20 plant sites"
            ),
            "is_active": True,
        },
    )

    assert (
        create_response.status_code
        == 201
    )

    grow_bed_id = UUID(
        create_response.json()["id"]
    )

    update_response = await client.patch(
        (
            "/api/v1/grow-beds/"
            f"{grow_bed_id}"
        ),
        json={
            "name": "Updated Grow Bed",
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
            == grow_bed_id
        )
        .where(
            AuditLog.action
            == "update"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "update"
    assert audit.entity_type == "grow_bed"
    assert audit.entity_id == grow_bed_id
    assert audit.source == "api"

    assert audit.old_value == {
        "name": "Original Grow Bed",
        "is_active": True,
    }

    assert audit.new_value == {
        "name": "Updated Grow Bed",
        "is_active": False,
    }


# ============================================================
# DELETE
# ============================================================


async def test_admin_delete_grow_bed_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    system = await create_system(
        test_session
    )

    await use_current_user(
        admin
    )

    create_response = await client.post(
        "/api/v1/grow-beds",
        json={
            "system_id": str(
                system.id
            ),
            "name": "Delete Grow Bed",
            "crop_type": "Lettuce",
            "capacity_description": (
                "20 plant sites"
            ),
            "is_active": True,
        },
    )

    assert (
        create_response.status_code
        == 201
    )

    grow_bed_id = UUID(
        create_response.json()["id"]
    )

    delete_response = await client.delete(
        (
            "/api/v1/grow-beds/"
            f"{grow_bed_id}"
        )
    )

    assert (
        delete_response.status_code
        == 204
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == grow_bed_id
        )
        .where(
            AuditLog.action
            == "delete"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "delete"
    assert audit.entity_type == "grow_bed"
    assert audit.entity_id == grow_bed_id
    assert audit.source == "api"

    assert audit.old_value == {
        "deleted_at": None,
    }

    assert (
        audit.new_value["deleted_at"]
        is not None
    )


# ============================================================
# AUTHORIZATION
# ============================================================


async def test_non_admin_cannot_create_grow_bed(
    test_session,
    client,
):
    system = await create_system(
        test_session
    )

    non_admin = SimpleNamespace(
        role="non-admin",
    )

    await use_current_user(
        non_admin
    )

    response = await client.post(
        "/api/v1/grow-beds",
        json={
            "system_id": str(
                system.id
            ),
            "name": "Forbidden Grow Bed",
            "crop_type": "Lettuce",
            "capacity_description": (
                "20 plant sites"
            ),
            "is_active": True,
        },
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_all_grow_bed_mutations_require_admin():
    expected = {
        (
            "POST",
            "/grow-beds",
        ),
        (
            "PATCH",
            "/grow-beds/{grow_bed_id}",
        ),
        (
            "DELETE",
            "/grow-beds/{grow_bed_id}",
        ),
    }

    discovered = set()

    for route_item in router.routes:
        if not isinstance(
            route_item,
            APIRoute,
        ):
            continue

        for method in (
            route_item.methods or set()
        ):
            route_key = (
                method,
                route_item.path,
            )

            if route_key not in expected:
                continue

            discovered.add(
                route_key
            )

            dependency_calls = {
                dependency.call
                for dependency
                in route_item.dependant.dependencies
            }

            assert (
                require_admin
                in dependency_calls
            ), (
                f"{method} "
                f"{route_item.path} "
                "is missing admin authorization"
            )

    assert discovered == expected