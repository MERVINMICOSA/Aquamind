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
from app.api.sensor_calibrations import router
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
        username="sensor-calibration-audit-admin",
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


async def create_parent_sensor(
    client,
):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": (
                "Sensor Calibration "
                "Audit System"
            ),
            "description": None,
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

    sensor_response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": (
                "Calibration Audit "
                "pH Sensor"
            ),
            "sensor_type": "ph",
            "measurement_type": "ph",
            "location_type": "tank",
            "location_id": None,
            "unit": "pH",
            "hardware_identifier": (
                "PH-CAL-AUDIT-001"
            ),
            "is_simulated": True,
            "is_enabled": True,
            "sampling_interval_seconds": 10,
            "calibration_status": "pending",
        },
    )

    assert (
        sensor_response.status_code
        == 201
    )

    return UUID(
        sensor_response.json()["id"]
    )


def build_calibration_payload(
    sensor_id: UUID,
):
    return {
        "sensor_id": str(
            sensor_id
        ),
        "offset": 0.15,
        "factor": 1.02,
        "calibration_data": {
            "reference_value": 7.00,
            "measured_value": 6.85,
            "instrument": (
                "laboratory_reference"
            ),
        },
        "performed_at": (
            "2026-01-01T10:00:00Z"
        ),
        "verified_by_user_id": None,
        "status": "verified",
        "notes": (
            "Initial pH sensor calibration."
        ),
    }


# ============================================================
# CREATE
# ============================================================


async def test_admin_create_sensor_calibration_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    sensor_id = await create_parent_sensor(
        client
    )

    response = await client.post(
        "/api/v1/sensor-calibrations",
        json=build_calibration_payload(
            sensor_id
        ),
    )

    assert response.status_code == 201

    calibration = response.json()

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
        == "sensor_calibration"
    )

    assert (
        audit.entity_id
        == calibration_id
    )

    assert audit.source == "api"
    assert audit.old_value is None

    assert (
        audit.new_value["sensor_id"]
        == str(sensor_id)
    )

    assert (
        audit.new_value["offset"]
        == 0.15
    )

    assert (
        audit.new_value["factor"]
        == 1.02
    )

    assert audit.new_value[
        "calibration_data"
    ] == {
        "reference_value": 7.00,
        "measured_value": 6.85,
        "instrument": (
            "laboratory_reference"
        ),
    }

    assert audit.new_value[
        "performed_at"
    ].startswith(
        "2026-01-01T10:00:00"
    )

    assert (
        audit.new_value[
            "verified_by_user_id"
        ]
        is None
    )

    assert (
        audit.new_value["status"]
        == "verified"
    )

    assert (
        audit.new_value["notes"]
        == (
            "Initial pH sensor "
            "calibration."
        )
    )


# ============================================================
# UPDATE
# ============================================================


async def test_admin_update_sensor_calibration_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    sensor_id = await create_parent_sensor(
        client
    )

    create_response = await client.post(
        "/api/v1/sensor-calibrations",
        json=build_calibration_payload(
            sensor_id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    calibration_id = UUID(
        create_response.json()["id"]
    )

    update_response = await client.patch(
        (
            "/api/v1/sensor-calibrations/"
            f"{calibration_id}"
        ),
        json={
            "offset": 0.10,
            "factor": 1.01,
            "status": "verified",
            "notes": (
                "Calibration updated "
                "after verification."
            ),
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
        == "sensor_calibration"
    )

    assert (
        audit.entity_id
        == calibration_id
    )

    assert audit.source == "api"

    assert audit.old_value == {
        "offset": 0.15,
        "factor": 1.02,
        "status": "verified",
        "notes": (
            "Initial pH sensor calibration."
        ),
    }

    assert audit.new_value == {
        "offset": 0.10,
        "factor": 1.01,
        "status": "verified",
        "notes": (
            "Calibration updated "
            "after verification."
        ),
    }


# ============================================================
# DELETE
# ============================================================


async def test_admin_delete_sensor_calibration_creates_audit_log(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    await use_current_user(
        admin
    )

    sensor_id = await create_parent_sensor(
        client
    )

    create_response = await client.post(
        "/api/v1/sensor-calibrations",
        json=build_calibration_payload(
            sensor_id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    calibration_id = UUID(
        create_response.json()["id"]
    )

    delete_response = await client.delete(
        (
            "/api/v1/sensor-calibrations/"
            f"{calibration_id}"
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
        == "sensor_calibration"
    )

    assert (
        audit.entity_id
        == calibration_id
    )

    assert audit.source == "api"

    # Hard delete: previous record state is
    # preserved in old_value.
    assert (
        audit.old_value["sensor_id"]
        == str(sensor_id)
    )

    assert (
        audit.old_value["offset"]
        == 0.15
    )

    assert (
        audit.old_value["factor"]
        == 1.02
    )

    assert audit.old_value[
        "calibration_data"
    ] == {
        "reference_value": 7.00,
        "measured_value": 6.85,
        "instrument": (
            "laboratory_reference"
        ),
    }

    assert audit.old_value[
        "performed_at"
    ].startswith(
        "2026-01-01T10:00:00"
    )

    assert (
        audit.old_value[
            "verified_by_user_id"
        ]
        is None
    )

    assert (
        audit.old_value["status"]
        == "verified"
    )

    assert (
        audit.old_value["notes"]
        == (
            "Initial pH sensor "
            "calibration."
        )
    )

    assert audit.new_value is None

    # Confirm the actual calibration row is gone.
    get_response = await client.get(
        (
            "/api/v1/sensor-calibrations/"
            f"{calibration_id}"
        )
    )

    assert (
        get_response.status_code
        == 404
    )


# ============================================================
# AUTHORIZATION
# ============================================================


async def test_non_admin_cannot_create_sensor_calibration(
    test_session,
    client,
):
    admin = await create_admin(
        test_session
    )

    # Parent records must be created while an admin
    # is authenticated because their mutation routes
    # are already protected.
    await use_current_user(
        admin
    )

    sensor_id = await create_parent_sensor(
        client
    )

    non_admin = SimpleNamespace(
        role="non-admin",
    )

    await use_current_user(
        non_admin
    )

    response = await client.post(
        "/api/v1/sensor-calibrations",
        json=build_calibration_payload(
            sensor_id
        ),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_all_sensor_calibration_mutations_require_admin():
    expected = {
        (
            "POST",
            "/sensor-calibrations",
        ),
        (
            "PATCH",
            (
                "/sensor-calibrations/"
                "{calibration_id}"
            ),
        ),
        (
            "DELETE",
            (
                "/sensor-calibrations/"
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