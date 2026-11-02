from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.api.alert_thresholds import router
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
        username="alert-threshold-audit-admin",
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


def build_threshold_payload():
    return {
        "sensor_type": "ph",
        "measurement_type": "ph",
        "warning_low": 6.5,
        "warning_high": 7.5,
        "critical_low": 6.0,
        "critical_high": 8.0,
        "cooldown_seconds": 900,
        "enabled": True,
    }


# ============================================================
# CREATE
# ============================================================


async def test_admin_create_alert_threshold_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    payload = build_threshold_payload()

    # Attempt to spoof another updater.
    payload["updated_by_user_id"] = str(
        uuid4()
    )

    response = await client.post(
        "/api/v1/alert-thresholds",
        json=payload,
    )

    assert response.status_code == 201

    threshold = response.json()

    threshold_id = UUID(
        threshold["id"]
    )

    # Authenticated admin must override the
    # client-supplied updater UUID.
    assert (
        threshold["updated_by_user_id"]
        == str(admin.id)
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == threshold_id
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
        == "alert_threshold"
    )

    assert (
        audit.entity_id
        == threshold_id
    )

    assert audit.source == "api"
    assert audit.old_value is None

    assert (
        audit.new_value["sensor_type"]
        == "ph"
    )

    assert (
        audit.new_value[
            "measurement_type"
        ]
        == "ph"
    )

    assert (
        audit.new_value["warning_low"]
        == 6.5
    )

    assert (
        audit.new_value["warning_high"]
        == 7.5
    )

    assert (
        audit.new_value["critical_low"]
        == 6.0
    )

    assert (
        audit.new_value["critical_high"]
        == 8.0
    )

    assert (
        audit.new_value[
            "cooldown_seconds"
        ]
        == 900
    )

    assert (
        audit.new_value["enabled"]
        is True
    )

    assert (
        audit.new_value[
            "updated_by_user_id"
        ]
        == str(admin.id)
    )

    assert (
        audit.new_value["updated_at"]
        is not None
    )


# ============================================================
# UPDATE
# ============================================================


async def test_admin_update_alert_threshold_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    create_response = await client.post(
        "/api/v1/alert-thresholds",
        json=build_threshold_payload(),
    )

    assert (
        create_response.status_code
        == 201
    )

    threshold_id = UUID(
        create_response.json()["id"]
    )

    update_response = await client.patch(
        (
            "/api/v1/alert-thresholds/"
            f"{threshold_id}"
        ),
        json={
            "warning_low": 6.4,
            "critical_low": 5.9,
            "cooldown_seconds": 600,
            "enabled": False,

            # Must be ignored.
            "updated_by_user_id": str(
                uuid4()
            ),
        },
    )

    assert (
        update_response.status_code
        == 200
    )

    updated = update_response.json()

    assert (
        updated["updated_by_user_id"]
        == str(admin.id)
    )

    assert (
        updated["warning_low"]
        == 6.4
    )

    assert (
        updated["critical_low"]
        == 5.9
    )

    assert (
        updated["cooldown_seconds"]
        == 600
    )

    assert (
        updated["enabled"]
        is False
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == threshold_id
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
        == "alert_threshold"
    )

    assert audit.old_value == {
        "warning_low": 6.5,
        "critical_low": 6.0,
        "cooldown_seconds": 900,
        "enabled": True,
    }

    assert audit.new_value == {
        "warning_low": 6.4,
        "critical_low": 5.9,
        "cooldown_seconds": 600,
        "enabled": False,
    }


# ============================================================
# DELETE
# ============================================================


async def test_admin_delete_alert_threshold_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    create_response = await client.post(
        "/api/v1/alert-thresholds",
        json=build_threshold_payload(),
    )

    assert (
        create_response.status_code
        == 201
    )

    threshold_id = UUID(
        create_response.json()["id"]
    )

    delete_response = await client.delete(
        (
            "/api/v1/alert-thresholds/"
            f"{threshold_id}"
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
            == threshold_id
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
        == "alert_threshold"
    )

    assert (
        audit.entity_id
        == threshold_id
    )

    assert audit.source == "api"

    assert (
        audit.old_value["sensor_type"]
        == "ph"
    )

    assert (
        audit.old_value[
            "measurement_type"
        ]
        == "ph"
    )

    assert (
        audit.old_value["warning_low"]
        == 6.5
    )

    assert (
        audit.old_value["critical_low"]
        == 6.0
    )

    assert (
        audit.old_value[
            "updated_by_user_id"
        ]
        == str(admin.id)
    )

    assert audit.new_value is None

    get_response = await client.get(
        (
            "/api/v1/alert-thresholds/"
            f"{threshold_id}"
        )
    )

    assert (
        get_response.status_code
        == 404
    )


# ============================================================
# AUTHORIZATION
# ============================================================


async def test_non_admin_cannot_create_alert_threshold(
    client,
):
    non_admin = SimpleNamespace(
        role="non-admin",
    )

    await use_current_user(
        non_admin
    )

    response = await client.post(
        "/api/v1/alert-thresholds",
        json=build_threshold_payload(),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_all_alert_threshold_mutations_require_admin():
    expected = {
        (
            "POST",
            "/alert-thresholds",
        ),
        (
            "PATCH",
            (
                "/alert-thresholds/"
                "{threshold_id}"
            ),
        ),
        (
            "DELETE",
            (
                "/alert-thresholds/"
                "{threshold_id}"
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