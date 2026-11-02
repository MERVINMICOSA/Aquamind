from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.api.automation_runs import router
from app.api.dependencies import (
    get_current_user,
    require_admin,
)
from app.db.enums import UserRole
from app.main import app
from app.models.other import AuditLog
from app.models.system import User


pytestmark = pytest.mark.asyncio


# ============================================================
# HELPERS
# ============================================================


async def create_admin(
    session,
):
    user = User(
        username="automation-run-audit-admin",
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


async def use_current_user(
    user,
):
    async def override_get_current_user():
        return user

    app.dependency_overrides[
        get_current_user
    ] = override_get_current_user


async def create_parent_rule(
    client,
):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Automation Run Audit System",
            "description": (
                "System for automation-run "
                "authorization testing."
            ),
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert (
        system_response.status_code
        == 201
    )

    system_id = (
        system_response.json()["id"]
    )

    rule_response = await client.post(
        "/api/v1/automation-rules",
        json={
            "system_id": system_id,
            "name": "Audit Scheduled Pump Rule",
            "description": (
                "Scheduled pump automation."
            ),
            "trigger_type": "schedule",
            "condition_definition": {
                "schedule": "0 * * * *",
            },
            "action_definition": {
                "action": "activate_actuator",
                "actuator_type": "water_pump",
                "value": 1.0,
            },
            "enabled": True,
            "priority": 5,
            "cooldown_seconds": 60,
        },
    )

    assert (
        rule_response.status_code
        == 201
    )

    return UUID(
        rule_response.json()["id"]
    )


def build_run_payload(
    rule_id: UUID,
):
    return {
        "rule_id": str(
            rule_id
        ),
        "started_at": (
            "2026-01-01T12:00:00Z"
        ),
        "completed_at": (
            "2026-01-01T12:00:05Z"
        ),
        "trigger_value": 1.0,
        "status": "completed",
        "result_summary": (
            "Pump activated successfully."
        ),
        "error_message": None,
    }


# ============================================================
# RUNTIME CREATE / UPDATE POLICY
# ============================================================


async def test_automation_run_create_and_update_do_not_duplicate_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    rule_id = await create_parent_rule(
        client
    )

    create_response = await client.post(
        "/api/v1/automation-runs",
        json=build_run_payload(
            rule_id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    run_id = UUID(
        create_response.json()["id"]
    )

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id
            == run_id
        )
    )

    assert (
        result.scalars().all()
        == []
    )

    update_response = await client.patch(
        (
            "/api/v1/automation-runs/"
            f"{run_id}"
        ),
        json={
            "status": "failed",
            "completed_at": (
                "2026-01-01T12:00:10Z"
            ),
            "trigger_value": 0.95,
            "result_summary": (
                "Pump failed to reach "
                "expected state."
            ),
            "error_message": (
                "PUMP_TIMEOUT"
            ),
        },
    )

    assert (
        update_response.status_code
        == 200
    )

    result = await test_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id
            == run_id
        )
    )

    assert (
        result.scalars().all()
        == []
    )


# ============================================================
# DELETE AUDIT
# ============================================================


async def test_admin_delete_automation_run_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    rule_id = await create_parent_rule(
        client
    )

    create_response = await client.post(
        "/api/v1/automation-runs",
        json=build_run_payload(
            rule_id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    run_id = UUID(
        create_response.json()["id"]
    )

    delete_response = await client.delete(
        (
            "/api/v1/automation-runs/"
            f"{run_id}"
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
            == run_id
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
        == "automation_run"
    )

    assert (
        audit.entity_id
        == run_id
    )

    assert audit.source == "api"

    assert (
        audit.old_value["rule_id"]
        == str(rule_id)
    )

    assert (
        audit.old_value["status"]
        == "completed"
    )

    assert (
        audit.old_value["trigger_value"]
        == 1.0
    )

    assert (
        audit.old_value["result_summary"]
        == (
            "Pump activated successfully."
        )
    )

    assert (
        audit.old_value["error_message"]
        is None
    )

    assert (
        audit.old_value["started_at"]
        is not None
    )

    assert (
        audit.old_value["completed_at"]
        is not None
    )

    assert audit.new_value is None

    get_response = await client.get(
        (
            "/api/v1/automation-runs/"
            f"{run_id}"
        )
    )

    assert (
        get_response.status_code
        == 404
    )


# ============================================================
# DELETE AUTHORIZATION
# ============================================================


async def test_non_admin_cannot_delete_automation_run(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    rule_id = await create_parent_rule(
        client
    )

    create_response = await client.post(
        "/api/v1/automation-runs",
        json=build_run_payload(
            rule_id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    run_id = UUID(
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
            "/api/v1/automation-runs/"
            f"{run_id}"
        )
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


# ============================================================
# ROUTE POLICY
# ============================================================


async def test_automation_run_mutation_authorization_policy():
    expected = {
        (
            "POST",
            "/automation-runs",
        ),
        (
            "PATCH",
            "/automation-runs/{run_id}",
        ),
        (
            "DELETE",
            "/automation-runs/{run_id}",
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