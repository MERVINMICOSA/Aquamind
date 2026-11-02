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
from app.api.sensors import router
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
        username="sensors-audit-admin",
        password_hash="test-password-hash",
        role=UserRole.ADMIN,
        is_active=True,
    )

    session.add(user)

    await session.commit()
    await session.refresh(user)

    return user


async def create_system(
    session,
):
    system = AquaponicsSystem(
        name="Sensor Audit System",
        description=None,
        timezone="UTC",
        is_active=True,
    )

    session.add(system)

    await session.commit()
    await session.refresh(system)

    return system


async def use_current_user(
    user,
):
    async def override_get_current_user():
        return user

    app.dependency_overrides[
        get_current_user
    ] = override_get_current_user


def build_sensor_payload(
    system_id: UUID,
    *,
    name: str = "Audit Water Temperature Sensor",
):
    return {
        "system_id": str(system_id),
        "name": name,
        "sensor_type": "water_temperature",
        "measurement_type": "temperature",
        "location_type": "tank",
        "location_id": None,
        "unit": "Â°C",
        "hardware_identifier": "TEMP-AUDIT-001",
        "is_simulated": True,
        "is_enabled": True,
        "sampling_interval_seconds": 10,
        "calibration_status": "pending",
    }


# ============================================================
# CREATE
# ============================================================


async def test_admin_create_sensor_creates_audit_log(
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
        "/api/v1/sensors",
        json=build_sensor_payload(
            system.id
        ),
    )

    assert response.status_code == 201

    sensor = response.json()

    sensor_id = UUID(
        sensor["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == sensor_id
        )
        .where(
            AuditLog.action
            == "create"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "create"
    assert audit.entity_type == "sensor"
    assert audit.entity_id == sensor_id
    assert audit.source == "api"

    assert audit.old_value is None

    assert audit.new_value == {
        "system_id": str(system.id),
        "name": (
            "Audit Water Temperature Sensor"
        ),
        "sensor_type": (
            "water_temperature"
        ),
        "measurement_type": (
            "temperature"
        ),
        "location_type": "tank",
        "location_id": None,
        "unit": "Â°C",
        "hardware_identifier": (
            "TEMP-AUDIT-001"
        ),
        "is_simulated": True,
        "is_enabled": True,
        "sampling_interval_seconds": 10,
        "calibration_status": "pending",
    }


# ============================================================
# UPDATE
# ============================================================


async def test_admin_update_sensor_creates_audit_log(
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
        "/api/v1/sensors",
        json=build_sensor_payload(
            system.id,
            name=(
                "Original Water "
                "Temperature Sensor"
            ),
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    sensor_id = UUID(
        create_response.json()["id"]
    )

    update_response = await client.patch(
        f"/api/v1/sensors/{sensor_id}",
        json={
            "name": (
                "Updated Water "
                "Temperature Sensor"
            ),
            "sampling_interval_seconds": 30,
            "is_enabled": False,
            "calibration_status": "verified",
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
            == sensor_id
        )
        .where(
            AuditLog.action
            == "update"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "update"
    assert audit.entity_type == "sensor"
    assert audit.entity_id == sensor_id
    assert audit.source == "api"

    assert audit.old_value == {
        "name": (
            "Original Water "
            "Temperature Sensor"
        ),
        "sampling_interval_seconds": 10,
        "is_enabled": True,
        "calibration_status": "pending",
    }

    assert audit.new_value == {
        "name": (
            "Updated Water "
            "Temperature Sensor"
        ),
        "sampling_interval_seconds": 30,
        "is_enabled": False,
        "calibration_status": "verified",
    }


# ============================================================
# DELETE
# ============================================================


async def test_admin_delete_sensor_creates_audit_log(
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
        "/api/v1/sensors",
        json=build_sensor_payload(
            system.id,
            name="Delete Audit Sensor",
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    sensor_id = UUID(
        create_response.json()["id"]
    )

    delete_response = await client.delete(
        f"/api/v1/sensors/{sensor_id}"
    )

    assert (
        delete_response.status_code
        == 204
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == sensor_id
        )
        .where(
            AuditLog.action
            == "delete"
        )
    )

    audit = result.scalars().one()

    assert audit.user_id == admin.id
    assert audit.action == "delete"
    assert audit.entity_type == "sensor"
    assert audit.entity_id == sensor_id
    assert audit.source == "api"

    assert audit.old_value == {
        "deleted_at": None,
    }

    assert (
        audit.new_value["deleted_at"]
        is not None
    )


# ============================================================
# AUTHORIZATION
# ============================================================


async def test_non_admin_cannot_create_sensor(
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
        "/api/v1/sensors",
        json=build_sensor_payload(
            system.id,
            name="Forbidden Sensor",
        ),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_all_sensor_mutations_require_admin():
    expected = {
        (
            "POST",
            "/sensors",
        ),
        (
            "PATCH",
            "/sensors/{sensor_id}",
        ),
        (
            "DELETE",
            "/sensors/{sensor_id}",
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