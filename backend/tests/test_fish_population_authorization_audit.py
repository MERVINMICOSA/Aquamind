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
        username="fish-population-audit-admin",
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


async def create_tank(
    client,
):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Fish Population Audit System",
            "description": (
                "System for fish population "
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
            "name": "Fish Population Audit Tank",
            "capacity_liters": 1000,
            "species": "Tilapia",
            "is_active": True,
        },
    )

    assert tank_response.status_code == 201

    return tank_response.json()["id"]


def build_population_payload(
    tank_id: str,
):
    return {
        "tank_id": tank_id,
        "species": "Tilapia",
        "count": 100,
        "estimated_biomass_grams": 25000.0,
        "effective_at": (
            "2026-01-01T09:00:00Z"
        ),

        # Deliberately present so the test can
        # prove that client attribution is ignored.
        "recorded_by_user_id": str(
            uuid4()
        ),

        "notes": (
            "Initial population record."
        ),
    }


async def test_population_create_uses_authenticated_recorder_and_audits(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    tank_id = await create_tank(
        client
    )

    response = await client.post(
        "/api/v1/feeding/population",
        json=build_population_payload(
            tank_id
        ),
    )

    assert response.status_code == 201

    population = response.json()

    assert (
        population["recorded_by_user_id"]
        == str(admin.id)
    )

    population_id = UUID(
        population["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == population_id
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
        == "fish_population_record"
    )

    assert (
        audit.entity_id
        == population_id
    )

    assert audit.source == "api"
    assert audit.old_value is None

    assert (
        audit.new_value["tank_id"]
        == tank_id
    )

    assert (
        audit.new_value["species"]
        == "Tilapia"
    )

    assert (
        audit.new_value["count"]
        == 100
    )

    assert (
        audit.new_value[
            "estimated_biomass_grams"
        ]
        == 25000.0
    )

    assert (
        audit.new_value[
            "recorded_by_user_id"
        ]
        == str(admin.id)
    )


async def test_population_update_preserves_original_recorder_and_audits_modifier(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    tank_id = await create_tank(
        client
    )

    create_response = await client.post(
        "/api/v1/feeding/population",
        json=build_population_payload(
            tank_id
        ),
    )

    assert create_response.status_code == 201

    population_id = UUID(
        create_response.json()["id"]
    )

    original_recorder = (
        create_response.json()[
            "recorded_by_user_id"
        ]
    )

    spoofed_recorder = uuid4()

    response = await client.patch(
        (
            "/api/v1/feeding/population/"
            f"{population_id}"
        ),
        json={
            "count": 95,
            "estimated_biomass_grams": 24000.0,
            "notes": (
                "Population updated after sampling."
            ),
            "recorded_by_user_id": str(
                spoofed_recorder
            ),
        },
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["count"] == 95

    assert (
        updated["estimated_biomass_grams"]
        == 24000.0
    )

    assert (
        updated["recorded_by_user_id"]
        == original_recorder
    )

    assert (
        updated["recorded_by_user_id"]
        != str(spoofed_recorder)
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == population_id
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
        == "fish_population_record"
    )

    assert audit.old_value == {
        "count": 100,
        "estimated_biomass_grams": 25000.0,
        "notes": (
            "Initial population record."
        ),
    }

    assert audit.new_value == {
        "count": 95,
        "estimated_biomass_grams": 24000.0,
        "notes": (
            "Population updated after sampling."
        ),
    }


async def test_admin_delete_population_record_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    tank_id = await create_tank(
        client
    )

    create_response = await client.post(
        "/api/v1/feeding/population",
        json=build_population_payload(
            tank_id
        ),
    )

    assert create_response.status_code == 201

    population_id = UUID(
        create_response.json()["id"]
    )

    response = await client.delete(
        (
            "/api/v1/feeding/population/"
            f"{population_id}"
        )
    )

    assert response.status_code == 204

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == population_id
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
        == "fish_population_record"
    )

    assert (
        audit.entity_id
        == population_id
    )

    assert audit.source == "api"

    assert (
        audit.old_value["tank_id"]
        == tank_id
    )

    assert (
        audit.old_value["species"]
        == "Tilapia"
    )

    assert (
        audit.old_value["count"]
        == 100
    )

    assert (
        audit.old_value[
            "estimated_biomass_grams"
        ]
        == 25000.0
    )

    assert (
        audit.old_value[
            "recorded_by_user_id"
        ]
        == str(admin.id)
    )

    assert audit.new_value is None

    get_response = await client.get(
        (
            "/api/v1/feeding/population/"
            f"{population_id}"
        )
    )

    assert get_response.status_code == 404


async def test_non_admin_cannot_delete_population_record(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    tank_id = await create_tank(
        client
    )

    create_response = await client.post(
        "/api/v1/feeding/population",
        json=build_population_payload(
            tank_id
        ),
    )

    assert create_response.status_code == 201

    population_id = UUID(
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
        (
            "/api/v1/feeding/population/"
            f"{population_id}"
        )
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_population_mutation_authorization_policy():
    expected = {
        (
            "POST",
            "/feeding/population",
        ),
        (
            "PATCH",
            "/feeding/population/{record_id}",
        ),
        (
            "DELETE",
            "/feeding/population/{record_id}",
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
                    get_current_user
                    in dependency_calls
                )

                assert (
                    require_admin
                    not in dependency_calls
                )

            elif method == "DELETE":
                assert (
                    require_admin
                    in dependency_calls
                )

    assert discovered == expected