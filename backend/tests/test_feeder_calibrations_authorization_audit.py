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
        username="feeder-calibration-audit-admin",
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


async def create_feeder_actuator(
    client,
):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Feeder Calibration Audit System",
            "description": (
                "System for feeder calibration tests."
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
            "name": "Feeder Calibration Audit Tank",
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
            "name": "Calibration Audit Feeder",
            "actuator_type": "fish_feeder",
            "control_mode": "scheduled",
            "hardware_identifier": (
                "FEEDER-CAL-AUDIT-001"
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

    return actuator_response.json()["id"]


def build_calibration_payload(
    actuator_id: str,
):
    return {
        "actuator_id": actuator_id,
        "run_count": 5,
        "measured_seconds": 10.0,
        "measured_grams": 50.0,
        "grams_per_second": 5.0,
        "calibration_method": (
            "measured_average"
        ),
        "performed_at": (
            "2026-01-01T10:00:00Z"
        ),
        "verified_by_user_id": None,
        "notes": (
            "Initial feeder calibration."
        ),
    }


async def test_admin_create_feeder_calibration_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    actuator_id = (
        await create_feeder_actuator(
            client
        )
    )

    response = await client.post(
        "/api/v1/feeding/calibrations",
        json=build_calibration_payload(
            actuator_id
        ),
    )

    assert response.status_code == 201

    calibration = response.json()

    assert (
        calibration["verified_by_user_id"]
        is None
    )

    calibration_id = UUID(
        calibration["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == calibration_id
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
        == "feeder_calibration"
    )

    assert (
        audit.entity_id
        == calibration_id
    )

    assert audit.source == "api"
    assert audit.old_value is None

    assert (
        audit.new_value["actuator_id"]
        == actuator_id
    )

    assert (
        audit.new_value["run_count"]
        == 5
    )

    assert (
        audit.new_value[
            "measured_seconds"
        ]
        == 10.0
    )

    assert (
        audit.new_value[
            "measured_grams"
        ]
        == 50.0
    )

    assert (
        audit.new_value[
            "grams_per_second"
        ]
        == 5.0
    )

    assert (
        audit.new_value[
            "calibration_method"
        ]
        == "measured_average"
    )

    assert (
        audit.new_value[
            "verified_by_user_id"
        ]
        is None
    )


async def test_feeder_calibration_verification_uses_authenticated_admin(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    actuator_id = (
        await create_feeder_actuator(
            client
        )
    )

    create_response = await client.post(
        "/api/v1/feeding/calibrations",
        json=build_calibration_payload(
            actuator_id
        ),
    )

    assert create_response.status_code == 201

    calibration_id = UUID(
        create_response.json()["id"]
    )

    spoofed_user_id = uuid4()

    response = await client.patch(
        (
            "/api/v1/feeding/calibrations/"
            f"{calibration_id}"
        ),
        json={
            "grams_per_second": 5.25,
            "notes": (
                "Calibration verified and updated."
            ),
            "verified_by_user_id": str(
                spoofed_user_id
            ),
        },
    )

    assert response.status_code == 200

    updated = response.json()

    assert (
        updated["grams_per_second"]
        == 5.25
    )

    assert (
        updated["verified_by_user_id"]
        == str(admin.id)
    )

    assert (
        updated["verified_by_user_id"]
        != str(spoofed_user_id)
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == calibration_id
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
        == "feeder_calibration"
    )

    assert audit.old_value == {
        "grams_per_second": 5.0,
        "notes": (
            "Initial feeder calibration."
        ),
        "verified_by_user_id": None,
    }

    assert audit.new_value == {
        "grams_per_second": 5.25,
        "notes": (
            "Calibration verified and updated."
        ),
        "verified_by_user_id": str(
            admin.id
        ),
    }


async def test_admin_delete_feeder_calibration_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    actuator_id = (
        await create_feeder_actuator(
            client
        )
    )

    create_response = await client.post(
        "/api/v1/feeding/calibrations",
        json=build_calibration_payload(
            actuator_id
        ),
    )

    assert create_response.status_code == 201

    calibration_id = UUID(
        create_response.json()["id"]
    )

    response = await client.delete(
        (
            "/api/v1/feeding/calibrations/"
            f"{calibration_id}"
        )
    )

    assert response.status_code == 204

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == calibration_id
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
        == "feeder_calibration"
    )

    assert (
        audit.entity_id
        == calibration_id
    )

    assert audit.source == "api"

    assert (
        audit.old_value["actuator_id"]
        == actuator_id
    )

    assert (
        audit.old_value["run_count"]
        == 5
    )

    assert (
        audit.old_value[
            "calibration_method"
        ]
        == "measured_average"
    )

    assert audit.new_value is None

    get_response = await client.get(
        (
            "/api/v1/feeding/calibrations/"
            f"{calibration_id}"
        )
    )

    assert get_response.status_code == 404


async def test_non_admin_cannot_create_feeder_calibration(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    actuator_id = (
        await create_feeder_actuator(
            client
        )
    )

    non_admin = SimpleNamespace(
        role="non-admin",
    )

    await use_current_user(
        non_admin
    )

    response = await client.post(
        "/api/v1/feeding/calibrations",
        json=build_calibration_payload(
            actuator_id
        ),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_all_feeder_calibration_mutations_require_admin():
    expected = {
        (
            "POST",
            "/feeding/calibrations",
        ),
        (
            "PATCH",
            (
                "/feeding/calibrations/"
                "{calibration_id}"
            ),
        ),
        (
            "DELETE",
            (
                "/feeding/calibrations/"
                "{calibration_id}"
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