from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.api.actuators import router
from app.api.dependencies import (
    get_current_user,
    require_admin,
)
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
        username="actuators-audit-admin",
        password_hash="test-password-hash",
        role=UserRole.ADMIN,
        is_active=True,
    )

    session.add(
        user
    )

    await session.commit()
    await session.refresh(
        user
    )

    return user


async def create_system(
    session,
):
    system = AquaponicsSystem(
        name="Actuator Audit System",
        description=None,
        timezone="UTC",
        is_active=True,
    )

    session.add(
        system
    )

    await session.commit()
    await session.refresh(
        system
    )

    return system


async def use_current_user(
    user,
):
    async def override_get_current_user():
        return user

    app.dependency_overrides[
        get_current_user
    ] = override_get_current_user


def build_actuator_payload(
    system_id: UUID,
    *,
    name: str = "Audit Water Pump",
):
    return {
        "system_id": str(
            system_id
        ),
        "name": name,
        "actuator_type": "water_pump",
        "control_mode": "manual",
        "hardware_identifier": (
            "PUMP-AUDIT-001"
        ),
        "location_type": "tank",
        "is_enabled": True,
        "safety_config": {
            "max_runtime_seconds": 300,
        },
        "current_state": "off",
        "current_value": 0,
    }


# ============================================================
# CREATE
# ============================================================


async def test_admin_create_actuator_creates_audit_log(
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
        "/api/v1/actuators",
        json=build_actuator_payload(
            system.id
        ),
    )

    assert response.status_code == 201

    actuator = response.json()

    actuator_id = UUID(
        actuator["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == actuator_id
        )
        .where(
            AuditLog.action
            == "create"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "create"
    assert audit.entity_type == "actuator"

    assert (
        audit.entity_id
        == actuator_id
    )

    assert audit.source == "api"
    assert audit.old_value is None

    assert (
        audit.new_value["system_id"]
        == str(system.id)
    )

    assert (
        audit.new_value["name"]
        == "Audit Water Pump"
    )

    assert (
        audit.new_value["actuator_type"]
        == "water_pump"
    )

    assert (
        audit.new_value["control_mode"]
        == "manual"
    )

    assert (
        audit.new_value[
            "hardware_identifier"
        ]
        == "PUMP-AUDIT-001"
    )

    assert (
        audit.new_value["location_type"]
        == "tank"
    )

    assert (
        audit.new_value["is_enabled"]
        is True
    )

    assert audit.new_value[
        "safety_config"
    ] == {
        "max_runtime_seconds": 300,
    }

    assert (
        audit.new_value["current_state"]
        == "off"
    )

    assert (
        audit.new_value["current_value"]
        == 0.0
    )


# ============================================================
# UPDATE
# ============================================================


async def test_admin_update_actuator_creates_audit_log(
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
        "/api/v1/actuators",
        json=build_actuator_payload(
            system.id,
            name="Original Water Pump",
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    actuator_id = UUID(
        create_response.json()["id"]
    )

    update_response = await client.patch(
        f"/api/v1/actuators/{actuator_id}",
        json={
            "current_state": "on",
            "current_value": 1,
            "is_enabled": True,
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
            == actuator_id
        )
        .where(
            AuditLog.action
            == "update"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "update"
    assert audit.entity_type == "actuator"

    assert (
        audit.entity_id
        == actuator_id
    )

    assert audit.source == "api"

    assert audit.old_value == {
        "current_state": "off",
        "current_value": 0.0,
        "is_enabled": True,
    }

    assert audit.new_value == {
        "current_state": "on",
        "current_value": 1.0,
        "is_enabled": True,
    }


# ============================================================
# DELETE
# ============================================================


async def test_admin_delete_actuator_creates_audit_log(
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
        "/api/v1/actuators",
        json=build_actuator_payload(
            system.id,
            name="Delete Audit Pump",
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    actuator_id = UUID(
        create_response.json()["id"]
    )

    delete_response = await client.delete(
        f"/api/v1/actuators/{actuator_id}"
    )

    assert (
        delete_response.status_code
        == 204
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == actuator_id
        )
        .where(
            AuditLog.action
            == "delete"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "delete"
    assert audit.entity_type == "actuator"

    assert (
        audit.entity_id
        == actuator_id
    )

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


async def test_non_admin_cannot_create_actuator(
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
        "/api/v1/actuators",
        json=build_actuator_payload(
            system.id,
            name="Forbidden Actuator",
        ),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_all_actuator_mutations_require_admin():
    expected = {
        (
            "POST",
            "/actuators",
        ),
        (
            "PATCH",
            "/actuators/{actuator_id}",
        ),
        (
            "DELETE",
            "/actuators/{actuator_id}",
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