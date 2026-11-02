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
from app.api.system_events import router
from app.db.enums import UserRole
from app.main import app
from app.models.other import AuditLog
from app.models.system import User


pytestmark = pytest.mark.asyncio


async def create_admin(
    session,
):
    user = User(
        username="system-event-audit-admin",
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


async def create_system(
    client,
):
    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "System Event Audit System",
            "description": (
                "System for event authorization testing."
            ),
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def build_event_payload(
    system_id: str,
):
    return {
        "system_id": system_id,
        "event_type": "pump_started",
        "severity": "info",
        "message": (
            "Main circulation pump started."
        ),
        "event_metadata": {
            "source": "test",
        },
        "occurred_at": (
            "2026-01-01T12:00:00Z"
        ),
    }


async def test_system_event_create_and_update_do_not_duplicate_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    system_id = await create_system(
        client
    )

    create_response = await client.post(
        "/api/v1/system-events",
        json=build_event_payload(
            system_id
        ),
    )

    assert create_response.status_code == 201

    event_id = UUID(
        create_response.json()["id"]
    )

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id
            == event_id
        )
    )

    assert result.scalars().all() == []

    update_response = await client.patch(
        f"/api/v1/system-events/{event_id}",
        json={
            "severity": "warning",
            "message": (
                "Pump runtime exceeded "
                "expected duration."
            ),
            "event_metadata": {
                "source": "test",
                "runtime_seconds": 420,
            },
        },
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["severity"] == "warning"

    assert (
        updated["message"]
        == (
            "Pump runtime exceeded "
            "expected duration."
        )
    )

    assert (
        updated["event_metadata"][
            "runtime_seconds"
        ]
        == 420
    )

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id
            == event_id
        )
    )

    assert result.scalars().all() == []


async def test_admin_delete_system_event_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    system_id = await create_system(
        client
    )

    create_response = await client.post(
        "/api/v1/system-events",
        json=build_event_payload(
            system_id
        ),
    )

    assert create_response.status_code == 201

    event_id = UUID(
        create_response.json()["id"]
    )

    response = await client.delete(
        f"/api/v1/system-events/{event_id}"
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
        == "system_event"
    )

    assert audit.entity_id == event_id
    assert audit.source == "api"

    assert (
        audit.old_value["system_id"]
        == system_id
    )

    assert (
        audit.old_value["event_type"]
        == "pump_started"
    )

    assert (
        audit.old_value["severity"]
        == "info"
    )

    assert (
        audit.old_value["message"]
        == "Main circulation pump started."
    )

    assert audit.old_value[
        "event_metadata"
    ] == {
        "source": "test",
    }

    assert (
        audit.old_value["occurred_at"]
        is not None
    )

    assert audit.new_value is None

    get_response = await client.get(
        f"/api/v1/system-events/{event_id}"
    )

    assert get_response.status_code == 404


async def test_non_admin_cannot_delete_system_event(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    system_id = await create_system(
        client
    )

    create_response = await client.post(
        "/api/v1/system-events",
        json=build_event_payload(
            system_id
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
        f"/api/v1/system-events/{event_id}"
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_system_event_mutation_authorization_policy():
    expected = {
        (
            "POST",
            "/system-events",
        ),
        (
            "PATCH",
            "/system-events/{event_id}",
        ),
        (
            "DELETE",
            "/system-events/{event_id}",
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