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
from app.api.feeding import router
from app.db.enums import UserRole
from app.main import app
from app.models.other import AuditLog
from app.models.system import User


pytestmark = pytest.mark.asyncio


async def create_admin(
    session,
):
    user = User(
        username="feeding-schedule-audit-admin",
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


async def create_parent_resources(
    client,
):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Feeding Schedule Audit System",
            "description": (
                "System for feeding schedule "
                "authorization testing."
            ),
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert system_response.status_code == 201

    system_id = system_response.json()["id"]

    tank_response = await client.post(
        "/api/v1/tanks",
        json={
            "system_id": system_id,
            "name": "Feeding Schedule Audit Tank",
            "capacity_liters": 1000,
            "species": "Tilapia",
            "is_active": True,
        },
    )

    assert tank_response.status_code == 201

    tank_id = tank_response.json()["id"]

    actuator_response = await client.post(
        "/api/v1/actuators",
        json={
            "system_id": system_id,
            "name": "Feeding Schedule Audit Feeder",
            "actuator_type": "fish_feeder",
            "control_mode": "scheduled",
            "hardware_identifier": (
                "FEEDER-SCHEDULE-AUDIT-001"
            ),
            "location_type": "tank",
            "location_id": tank_id,
            "is_enabled": True,
            "safety_config": {
                "max_runtime_seconds": 30,
            },
            "current_state": "off",
            "current_value": None,
            "last_state_at": None,
        },
    )

    assert actuator_response.status_code == 201

    actuator_id = actuator_response.json()["id"]

    return system_id, actuator_id


def build_schedule_payload(
    system_id: str,
    actuator_id: str,
):
    return {
        "system_id": system_id,
        "actuator_id": actuator_id,
        "name": "Morning Feeding",
        "schedule_expression": "0 8 * * *",
        "enabled": True,
        "max_per_feed_grams": 100.0,
    }


async def test_admin_create_feeding_schedule_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    (
        system_id,
        actuator_id,
    ) = await create_parent_resources(
        client
    )

    response = await client.post(
        "/api/v1/feeding/schedules",
        json=build_schedule_payload(
            system_id,
            actuator_id,
        ),
    )

    assert response.status_code == 201

    schedule_id = UUID(
        response.json()["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == schedule_id
        )
        .where(
            AuditLog.action
            == "create"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "create"
    assert (
        audit.entity_type
        == "feeding_schedule"
    )
    assert audit.entity_id == schedule_id
    assert audit.source == "api"
    assert audit.old_value is None

    assert (
        audit.new_value["system_id"]
        == system_id
    )

    assert (
        audit.new_value["actuator_id"]
        == actuator_id
    )

    assert (
        audit.new_value["name"]
        == "Morning Feeding"
    )

    assert (
        audit.new_value[
            "schedule_expression"
        ]
        == "0 8 * * *"
    )

    assert audit.new_value[
        "enabled"
    ] is True

    assert (
        audit.new_value[
            "max_per_feed_grams"
        ]
        == 100.0
    )


async def test_admin_update_feeding_schedule_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    (
        system_id,
        actuator_id,
    ) = await create_parent_resources(
        client
    )

    create_response = await client.post(
        "/api/v1/feeding/schedules",
        json=build_schedule_payload(
            system_id,
            actuator_id,
        ),
    )

    assert create_response.status_code == 201

    schedule_id = UUID(
        create_response.json()["id"]
    )

    response = await client.patch(
        (
            "/api/v1/feeding/schedules/"
            f"{schedule_id}"
        ),
        json={
            "name": "Updated Morning Feeding",
            "max_per_feed_grams": 120.0,
            "enabled": False,
        },
    )

    assert response.status_code == 200

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == schedule_id
        )
        .where(
            AuditLog.action
            == "update"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert (
        audit.entity_type
        == "feeding_schedule"
    )

    assert audit.old_value == {
        "name": "Morning Feeding",
        "max_per_feed_grams": 100.0,
        "enabled": True,
    }

    assert audit.new_value == {
        "name": "Updated Morning Feeding",
        "max_per_feed_grams": 120.0,
        "enabled": False,
    }


async def test_admin_delete_feeding_schedule_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    (
        system_id,
        actuator_id,
    ) = await create_parent_resources(
        client
    )

    create_response = await client.post(
        "/api/v1/feeding/schedules",
        json=build_schedule_payload(
            system_id,
            actuator_id,
        ),
    )

    assert create_response.status_code == 201

    schedule_id = UUID(
        create_response.json()["id"]
    )

    response = await client.delete(
        (
            "/api/v1/feeding/schedules/"
            f"{schedule_id}"
        )
    )

    assert response.status_code == 204

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == schedule_id
        )
        .where(
            AuditLog.action
            == "delete"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "delete"
    assert (
        audit.entity_type
        == "feeding_schedule"
    )
    assert audit.entity_id == schedule_id
    assert audit.source == "api"

    assert (
        audit.old_value["system_id"]
        == system_id
    )

    assert (
        audit.old_value["actuator_id"]
        == actuator_id
    )

    assert (
        audit.old_value["name"]
        == "Morning Feeding"
    )

    assert audit.new_value is None

    get_response = await client.get(
        (
            "/api/v1/feeding/schedules/"
            f"{schedule_id}"
        )
    )

    assert get_response.status_code == 404


async def test_non_admin_cannot_create_feeding_schedule(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    (
        system_id,
        actuator_id,
    ) = await create_parent_resources(
        client
    )

    non_admin = SimpleNamespace(
        role="non-admin",
    )

    await use_current_user(
        non_admin
    )

    response = await client.post(
        "/api/v1/feeding/schedules",
        json=build_schedule_payload(
            system_id,
            actuator_id,
        ),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_all_feeding_schedule_mutations_require_admin():
    expected = {
        (
            "POST",
            "/feeding/schedules",
        ),
        (
            "PATCH",
            "/feeding/schedules/{schedule_id}",
        ),
        (
            "DELETE",
            "/feeding/schedules/{schedule_id}",
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