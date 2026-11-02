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
        username="feeding-event-audit-admin",
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


async def create_feeding_event_parents(
    client,
):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Feeding Event Audit System",
            "description": (
                "System for feeding event "
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
            "name": "Feeding Event Audit Tank",
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
            "name": "Feeding Event Audit Feeder",
            "actuator_type": "fish_feeder",
            "control_mode": "scheduled",
            "hardware_identifier": (
                "FEEDER-EVENT-AUDIT-001"
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

    actuator_event_response = await client.post(
        "/api/v1/actuator-events",
        json={
            "actuator_id": actuator_id,
            "command_type": "activate",
            "requested_value": 10.0,
            "actual_value": 10.0,
            "started_at": (
                "2026-01-01T08:00:00Z"
            ),
            "completed_at": (
                "2026-01-01T08:00:10Z"
            ),
            "duration_ms": 10000,
            "trigger_source": "schedule",
            "status": "completed",
            "fault_code": None,
            "error_message": None,
        },
    )

    assert (
        actuator_event_response.status_code
        == 201
    )

    actuator_event_id = (
        actuator_event_response.json()["id"]
    )

    return tank_id, actuator_event_id


def build_feeding_event_payload(
    tank_id: str,
    actuator_event_id: str,
):
    return {
        "schedule_id": None,
        "actuator_event_id": actuator_event_id,
        "tank_id": tank_id,
        "amount_grams": 50.0,
        "duration_seconds": 10.0,
        "calculated_from_biomass": 25000.0,
        "calibration_id": None,
        "executed_at": (
            "2026-01-01T08:00:10Z"
        ),
        "status": "completed",
        "notes": "Scheduled morning feeding.",
    }


async def test_feeding_event_create_and_update_do_not_duplicate_audit_log(
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
        tank_id,
        actuator_event_id,
    ) = await create_feeding_event_parents(
        client
    )

    create_response = await client.post(
        "/api/v1/feeding/events",
        json=build_feeding_event_payload(
            tank_id,
            actuator_event_id,
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
        f"/api/v1/feeding/events/{event_id}",
        json={
            "amount_grams": 55.0,
            "duration_seconds": 11.0,
            "notes": "Feeding event updated.",
        },
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["amount_grams"] == 55.0
    assert (
        updated["duration_seconds"]
        == 11.0
    )
    assert (
        updated["notes"]
        == "Feeding event updated."
    )

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id == event_id
        )
    )

    assert result.scalars().all() == []


async def test_admin_delete_feeding_event_creates_audit_log(
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
        tank_id,
        actuator_event_id,
    ) = await create_feeding_event_parents(
        client
    )

    create_response = await client.post(
        "/api/v1/feeding/events",
        json=build_feeding_event_payload(
            tank_id,
            actuator_event_id,
        ),
    )

    assert create_response.status_code == 201

    event_id = UUID(
        create_response.json()["id"]
    )

    response = await client.delete(
        f"/api/v1/feeding/events/{event_id}"
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
        == "feeding_event"
    )

    assert audit.entity_id == event_id
    assert audit.source == "api"

    assert audit.old_value[
        "schedule_id"
    ] is None

    assert (
        audit.old_value[
            "actuator_event_id"
        ]
        == actuator_event_id
    )

    assert (
        audit.old_value["tank_id"]
        == tank_id
    )

    assert (
        audit.old_value["amount_grams"]
        == 50.0
    )

    assert (
        audit.old_value[
            "duration_seconds"
        ]
        == 10.0
    )

    assert (
        audit.old_value[
            "calculated_from_biomass"
        ]
        == 25000.0
    )

    assert (
        audit.old_value["status"]
        == "completed"
    )

    assert audit.new_value is None

    get_response = await client.get(
        f"/api/v1/feeding/events/{event_id}"
    )

    assert get_response.status_code == 404


async def test_non_admin_cannot_delete_feeding_event(
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
        tank_id,
        actuator_event_id,
    ) = await create_feeding_event_parents(
        client
    )

    create_response = await client.post(
        "/api/v1/feeding/events",
        json=build_feeding_event_payload(
            tank_id,
            actuator_event_id,
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
        f"/api/v1/feeding/events/{event_id}"
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_feeding_event_mutation_authorization_policy():
    expected = {
        (
            "POST",
            "/feeding/events",
        ),
        (
            "PATCH",
            "/feeding/events/{event_id}",
        ),
        (
            "DELETE",
            "/feeding/events/{event_id}",
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