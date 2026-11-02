from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.api.dependencies import (
    get_current_user,
    require_admin,
)
from app.api.refill import router
from app.db.enums import UserRole
from app.main import app
from app.models.other import AuditLog
from app.models.system import User


pytestmark = pytest.mark.asyncio


async def create_admin(
    session,
):
    user = User(
        username="refill-audit-admin",
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


async def create_refill_parents(
    client,
):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Refill Audit System",
            "description": (
                "System for refill authorization testing."
            ),
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert system_response.status_code == 201

    system_id = system_response.json()["id"]

    reservoir_response = await client.post(
        "/api/v1/reservoirs",
        json={
            "system_id": system_id,
            "name": "Refill Audit Reservoir",
            "capacity_liters": 1000,
            "is_active": True,
        },
    )

    assert reservoir_response.status_code == 201

    reservoir_id = (
        reservoir_response.json()["id"]
    )

    tank_response = await client.post(
        "/api/v1/tanks",
        json={
            "system_id": system_id,
            "name": "Refill Audit Tank",
            "capacity_liters": 500,
            "species": "Tilapia",
            "is_active": True,
        },
    )

    assert tank_response.status_code == 201

    tank_id = tank_response.json()["id"]

    return reservoir_id, tank_id


def build_refill_payload(
    reservoir_id: str,
    tank_id: str,
):
    return {
        "reservoir_id": reservoir_id,
        "target_tank_id": tank_id,
        "start_level_percent": 20.0,
        "end_level_percent": 80.0,
        "started_at": (
            "2026-01-01T10:00:00Z"
        ),
        "completed_at": (
            "2026-01-01T10:05:00Z"
        ),
        "duration_seconds": 300,
        "trigger": "manual",
        "status": "completed",
        "timeout_reason": None,
    }


async def test_refill_create_and_update_do_not_duplicate_audit_log(
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
        reservoir_id,
        tank_id,
    ) = await create_refill_parents(
        client
    )

    create_response = await client.post(
        "/api/v1/refill-events",
        json=build_refill_payload(
            reservoir_id,
            tank_id,
        ),
    )

    assert create_response.status_code == 201

    event_id = UUID(
        create_response.json()["id"]
    )

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id == event_id
        )
    )

    assert result.scalars().all() == []

    update_response = await client.patch(
        f"/api/v1/refill-events/{event_id}",
        json={
            "end_level_percent": 90.0,
            "duration_seconds": 360,
            "status": "completed",
        },
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert (
        updated["end_level_percent"]
        == 90.0
    )

    assert (
        updated["duration_seconds"]
        == 360.0
    )

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id == event_id
        )
    )

    assert result.scalars().all() == []


async def test_admin_delete_refill_event_creates_audit_log(
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
        reservoir_id,
        tank_id,
    ) = await create_refill_parents(
        client
    )

    create_response = await client.post(
        "/api/v1/refill-events",
        json=build_refill_payload(
            reservoir_id,
            tank_id,
        ),
    )

    assert create_response.status_code == 201

    event_id = UUID(
        create_response.json()["id"]
    )

    response = await client.delete(
        f"/api/v1/refill-events/{event_id}"
    )

    assert response.status_code == 204

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == event_id
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
        == "refill_event"
    )

    assert audit.entity_id == event_id
    assert audit.source == "api"

    assert (
        audit.old_value["reservoir_id"]
        == reservoir_id
    )

    assert (
        audit.old_value["target_tank_id"]
        == tank_id
    )

    assert (
        audit.old_value[
            "start_level_percent"
        ]
        == 20.0
    )

    assert (
        audit.old_value[
            "end_level_percent"
        ]
        == 80.0
    )

    assert (
        audit.old_value[
            "duration_seconds"
        ]
        == 300.0
    )

    assert (
        audit.old_value["trigger"]
        == "manual"
    )

    assert (
        audit.old_value["status"]
        == "completed"
    )

    assert (
        audit.old_value["timeout_reason"]
        is None
    )

    assert audit.new_value is None

    get_response = await client.get(
        f"/api/v1/refill-events/{event_id}"
    )

    assert get_response.status_code == 404


async def test_non_admin_cannot_delete_refill_event(
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
        reservoir_id,
        tank_id,
    ) = await create_refill_parents(
        client
    )

    create_response = await client.post(
        "/api/v1/refill-events",
        json=build_refill_payload(
            reservoir_id,
            tank_id,
        ),
    )

    assert create_response.status_code == 201

    event_id = UUID(
        create_response.json()["id"]
    )

    non_admin = SimpleNamespace(
        id=uuid4(),
        role="non-admin",
        is_active=True,
    )

    await use_current_user(
        non_admin
    )

    response = await client.delete(
        f"/api/v1/refill-events/{event_id}"
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_refill_mutation_authorization_policy():
    expected = {
        (
            "POST",
            "/refill-events",
        ),
        (
            "PATCH",
            (
                "/refill-events/"
                "{refill_event_id}"
            ),
        ),
        (
            "DELETE",
            (
                "/refill-events/"
                "{refill_event_id}"
            ),
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

            if method in {
                "POST",
                "PATCH",
            }:
                assert (
                    require_admin
                    not in dependency_calls
                ), (
                    f"{method} "
                    f"{route_item.path} "
                    "must remain a runtime endpoint"
                )

            elif method == "DELETE":
                assert (
                    require_admin
                    in dependency_calls
                ), (
                    "DELETE "
                    f"{route_item.path} "
                    "must require administrator "
                    "authorization"
                )

    assert discovered == expected