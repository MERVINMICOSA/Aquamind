from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.api.automation_rules import router
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
        username="automation-rule-audit-admin",
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
        name="Automation Rule Audit System",
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


def build_rule_payload(
    system_id: UUID,
):
    return {
        "system_id": str(
            system_id
        ),
        "name": "Low pH Emergency Pump Rule",
        "description": (
            "Activates the pump when "
            "pH becomes too low."
        ),
        "trigger_type": "sensor_threshold",
        "condition_definition": {
            "sensor_type": "ph",
            "measurement_type": "ph",
            "operator": "less_than",
            "value": 6.0,
        },
        "action_definition": {
            "action": "activate_actuator",
            "actuator_type": "water_pump",
            "value": 1.0,
        },
        "enabled": True,
        "priority": 10,
        "cooldown_seconds": 300,
    }


# ============================================================
# CREATE
# ============================================================


async def test_admin_create_automation_rule_creates_audit_log(
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
        "/api/v1/automation-rules",
        json=build_rule_payload(
            system.id
        ),
    )

    assert response.status_code == 201

    rule = response.json()

    rule_id = UUID(
        rule["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == rule_id
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
        == "automation_rule"
    )

    assert (
        audit.entity_id
        == rule_id
    )

    assert audit.source == "api"
    assert audit.old_value is None

    assert (
        audit.new_value["system_id"]
        == str(system.id)
    )

    assert (
        audit.new_value["name"]
        == "Low pH Emergency Pump Rule"
    )

    assert (
        audit.new_value["trigger_type"]
        == "sensor_threshold"
    )

    assert audit.new_value[
        "condition_definition"
    ] == {
        "sensor_type": "ph",
        "measurement_type": "ph",
        "operator": "less_than",
        "value": 6.0,
    }

    assert audit.new_value[
        "action_definition"
    ] == {
        "action": "activate_actuator",
        "actuator_type": "water_pump",
        "value": 1.0,
    }

    assert (
        audit.new_value["enabled"]
        is True
    )

    assert (
        audit.new_value["priority"]
        == 10
    )

    assert (
        audit.new_value[
            "cooldown_seconds"
        ]
        == 300
    )


# ============================================================
# UPDATE
# ============================================================


async def test_admin_update_automation_rule_creates_audit_log(
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
        "/api/v1/automation-rules",
        json=build_rule_payload(
            system.id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    rule_id = UUID(
        create_response.json()["id"]
    )

    update_response = await client.patch(
        (
            "/api/v1/automation-rules/"
            f"{rule_id}"
        ),
        json={
            "name": (
                "Updated Low pH Pump Rule"
            ),
            "priority": 20,
            "cooldown_seconds": 600,
            "enabled": False,
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
            == rule_id
        )
        .where(
            AuditLog.action
            == "update"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "update"

    assert (
        audit.entity_type
        == "automation_rule"
    )

    assert audit.old_value == {
        "name": (
            "Low pH Emergency Pump Rule"
        ),
        "priority": 10,
        "cooldown_seconds": 300,
        "enabled": True,
    }

    assert audit.new_value == {
        "name": (
            "Updated Low pH Pump Rule"
        ),
        "priority": 20,
        "cooldown_seconds": 600,
        "enabled": False,
    }


# ============================================================
# DELETE
# ============================================================


async def test_admin_delete_automation_rule_creates_audit_log(
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
        "/api/v1/automation-rules",
        json=build_rule_payload(
            system.id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    rule_id = UUID(
        create_response.json()["id"]
    )

    delete_response = await client.delete(
        (
            "/api/v1/automation-rules/"
            f"{rule_id}"
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
            == rule_id
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
        == "automation_rule"
    )

    assert (
        audit.entity_id
        == rule_id
    )

    assert audit.source == "api"

    assert (
        audit.old_value["system_id"]
        == str(system.id)
    )

    assert (
        audit.old_value["name"]
        == "Low pH Emergency Pump Rule"
    )

    assert (
        audit.old_value["trigger_type"]
        == "sensor_threshold"
    )

    assert audit.old_value[
        "condition_definition"
    ] == {
        "sensor_type": "ph",
        "measurement_type": "ph",
        "operator": "less_than",
        "value": 6.0,
    }

    assert audit.old_value[
        "action_definition"
    ] == {
        "action": "activate_actuator",
        "actuator_type": "water_pump",
        "value": 1.0,
    }

    assert audit.new_value is None

    get_response = await client.get(
        (
            "/api/v1/automation-rules/"
            f"{rule_id}"
        )
    )

    assert (
        get_response.status_code
        == 404
    )


# ============================================================
# AUTHORIZATION
# ============================================================


async def test_non_admin_cannot_create_automation_rule(
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
        "/api/v1/automation-rules",
        json=build_rule_payload(
            system.id
        ),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_all_automation_rule_mutations_require_admin():
    expected = {
        (
            "POST",
            "/automation-rules",
        ),
        (
            "PATCH",
            (
                "/automation-rules/"
                "{rule_id}"
            ),
        ),
        (
            "DELETE",
            (
                "/automation-rules/"
                "{rule_id}"
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

            assert (
                require_admin
                in dependency_calls
            ), (
                f"{method} "
                f"{route_item.path} "
                "is missing admin authorization"
            )

    assert discovered == expected