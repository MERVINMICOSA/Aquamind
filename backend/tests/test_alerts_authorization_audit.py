from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.api.alerts import router
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
        username="alerts-audit-admin",
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
        name="Alert Audit System",
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


def build_alert_payload(
    system_id: UUID,
):
    return {
        "system_id": str(
            system_id
        ),
        "sensor_id": None,
        "actuator_id": None,
        "alert_type": "ph",
        "severity": "warning",
        "message": (
            "pH level is outside "
            "the normal range."
        ),
        "trigger_value": 6.3,
        "threshold_id": None,
        "status": "active",
    }


# ============================================================
# RUNTIME CREATE POLICY
# ============================================================


async def test_alert_creation_does_not_duplicate_audit_log(
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
        "/api/v1/alerts",
        json=build_alert_payload(
            system.id
        ),
    )

    assert response.status_code == 201

    alert_id = UUID(
        response.json()["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == alert_id
        )
    )

    assert (
        result.scalars().all()
        == []
    )


# ============================================================
# ACKNOWLEDGEMENT
# ============================================================


async def test_acknowledgement_uses_authenticated_user_and_audits(
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
        "/api/v1/alerts",
        json=build_alert_payload(
            system.id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    alert_id = UUID(
        create_response.json()["id"]
    )

    spoofed_user_id = uuid4()

    response = await client.patch(
        f"/api/v1/alerts/{alert_id}",
        json={
            "status": "acknowledged",

            # These client-supplied values must
            # not become authoritative.
            "acknowledged_by_user_id": str(
                spoofed_user_id
            ),
            "acknowledged_at": (
                "2000-01-01T00:00:00Z"
            ),
        },
    )

    assert response.status_code == 200

    acknowledged = response.json()

    assert (
        acknowledged["status"]
        == "acknowledged"
    )

    assert (
        acknowledged[
            "acknowledged_by_user_id"
        ]
        == str(admin.id)
    )

    assert (
        acknowledged["acknowledged_at"]
        is not None
    )

    assert not (
        acknowledged["acknowledged_at"]
        .startswith(
            "2000-01-01T00:00:00"
        )
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == alert_id
        )
        .where(
            AuditLog.action
            == "acknowledge"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id

    assert (
        audit.entity_type
        == "alert"
    )

    assert (
        audit.entity_id
        == alert_id
    )

    assert audit.source == "api"

    assert (
        audit.old_value["status"]
        == "active"
    )

    assert (
        audit.old_value[
            "acknowledged_at"
        ]
        is None
    )

    assert (
        audit.old_value[
            "acknowledged_by_user_id"
        ]
        is None
    )

    assert (
        audit.new_value["status"]
        == "acknowledged"
    )

    assert (
        audit.new_value[
            "acknowledged_at"
        ]
        is not None
    )

    assert (
        audit.new_value[
            "acknowledged_by_user_id"
        ]
        == str(admin.id)
    )


# ============================================================
# RESOLUTION
# ============================================================


async def test_resolution_creates_update_audit_log(
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
        "/api/v1/alerts",
        json=build_alert_payload(
            system.id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    alert_id = UUID(
        create_response.json()["id"]
    )

    response = await client.patch(
        f"/api/v1/alerts/{alert_id}",
        json={
            "status": "resolved",
            "resolution_reason": (
                "pH returned to "
                "normal range."
            ),

            # Server controls resolved_at.
            "resolved_at": (
                "2000-01-01T00:00:00Z"
            ),
        },
    )

    assert response.status_code == 200

    resolved = response.json()

    assert (
        resolved["status"]
        == "resolved"
    )

    assert (
        resolved["resolution_reason"]
        == (
            "pH returned to "
            "normal range."
        )
    )

    assert (
        resolved["resolved_at"]
        is not None
    )

    assert not (
        resolved["resolved_at"]
        .startswith(
            "2000-01-01T00:00:00"
        )
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == alert_id
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
        == "alert"
    )

    assert (
        audit.old_value["status"]
        == "active"
    )

    assert (
        audit.old_value[
            "resolution_reason"
        ]
        is None
    )

    assert (
        audit.old_value[
            "resolved_at"
        ]
        is None
    )

    assert (
        audit.new_value["status"]
        == "resolved"
    )

    assert (
        audit.new_value[
            "resolution_reason"
        ]
        == (
            "pH returned to "
            "normal range."
        )
    )

    assert (
        audit.new_value["resolved_at"]
        is not None
    )


# ============================================================
# DELETE
# ============================================================


async def test_admin_delete_alert_creates_audit_log(
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
        "/api/v1/alerts",
        json=build_alert_payload(
            system.id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    alert_id = UUID(
        create_response.json()["id"]
    )

    delete_response = await client.delete(
        f"/api/v1/alerts/{alert_id}"
    )

    assert (
        delete_response.status_code
        == 204
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == alert_id
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
        == "alert"
    )

    assert (
        audit.entity_id
        == alert_id
    )

    assert audit.source == "api"

    assert (
        audit.old_value["system_id"]
        == str(system.id)
    )

    assert (
        audit.old_value["alert_type"]
        == "ph"
    )

    assert (
        audit.old_value["severity"]
        == "warning"
    )

    assert (
        audit.old_value["status"]
        == "active"
    )

    assert (
        audit.old_value["message"]
        == (
            "pH level is outside "
            "the normal range."
        )
    )

    assert audit.new_value is None

    get_response = await client.get(
        f"/api/v1/alerts/{alert_id}"
    )

    assert (
        get_response.status_code
        == 404
    )


# ============================================================
# AUTHORIZATION
# ============================================================


async def test_non_admin_cannot_delete_alert(
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
        "/api/v1/alerts",
        json=build_alert_payload(
            system.id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    alert_id = UUID(
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
        f"/api/v1/alerts/{alert_id}"
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


async def test_alert_mutation_authorization_policy():
    expected = {
        (
            "POST",
            "/alerts",
        ),
        (
            "PATCH",
            "/alerts/{alert_id}",
        ),
        (
            "DELETE",
            "/alerts/{alert_id}",
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

            if method == "POST":
                assert (
                    require_admin
                    not in dependency_calls
                )

            elif method == "PATCH":
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