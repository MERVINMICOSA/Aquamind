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
from app.api.system_settings import router
from app.db.enums import UserRole
from app.main import app
from app.models.other import AuditLog
from app.models.system import (
    AquaponicsSystem,
    User,
)


pytestmark = pytest.mark.asyncio


async def create_admin(
    session,
):
    user = User(
        username="system-setting-audit-admin",
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
        name="System Setting Audit System",
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


def build_setting_payload(
    system_id: UUID,
):
    return {
        "system_id": str(
            system_id
        ),
        "setting_key": (
            "water_temperature_target"
        ),
        "setting_value": "26.5",
        "value_type": "float",
    }


async def test_admin_create_system_setting_creates_audit_log(
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
        "/api/v1/system-settings",
        json=build_setting_payload(
            system.id
        ),
    )

    assert response.status_code == 201

    setting = response.json()

    assert (
        setting["updated_by_user_id"]
        == str(admin.id)
    )

    setting_id = UUID(
        setting["id"]
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == setting_id
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
        == "system_setting"
    )

    assert (
        audit.entity_id
        == setting_id
    )

    assert audit.source == "api"
    assert audit.old_value is None

    assert (
        audit.new_value["system_id"]
        == str(system.id)
    )

    assert (
        audit.new_value["setting_key"]
        == "water_temperature_target"
    )

    assert (
        audit.new_value["setting_value"]
        == "26.5"
    )

    assert (
        audit.new_value["value_type"]
        == "float"
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

    assert (
        audit.new_value["deleted_at"]
        is None
    )


async def test_admin_update_system_setting_creates_audit_log(
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
        "/api/v1/system-settings",
        json=build_setting_payload(
            system.id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    setting_id = UUID(
        create_response.json()["id"]
    )

    response = await client.patch(
        (
            "/api/v1/system-settings/"
            f"{setting_id}"
        ),
        json={
            "setting_value": "27.0",
            "value_type": "float",
        },
    )

    assert response.status_code == 200

    updated = response.json()

    assert (
        updated["setting_value"]
        == "27.0"
    )

    assert (
        updated["updated_by_user_id"]
        == str(admin.id)
    )

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == setting_id
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
        == "system_setting"
    )

    assert (
        audit.old_value[
            "setting_value"
        ]
        == "26.5"
    )

    assert (
        audit.new_value[
            "setting_value"
        ]
        == "27.0"
    )

    assert (
        audit.new_value[
            "updated_by_user_id"
        ]
        == str(admin.id)
    )

    assert (
        audit.old_value["updated_at"]
        is not None
    )

    assert (
        audit.new_value["updated_at"]
        is not None
    )


async def test_admin_soft_delete_system_setting_creates_audit_log(
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
        "/api/v1/system-settings",
        json=build_setting_payload(
            system.id
        ),
    )

    assert (
        create_response.status_code
        == 201
    )

    setting_id = UUID(
        create_response.json()["id"]
    )

    response = await client.delete(
        (
            "/api/v1/system-settings/"
            f"{setting_id}"
        )
    )

    assert response.status_code == 204

    result = await test_session.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_id
            == setting_id
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
        == "system_setting"
    )

    assert audit.old_value[
        "deleted_at"
    ] is None

    assert (
        audit.new_value["deleted_at"]
        is not None
    )

    assert (
        audit.new_value[
            "updated_by_user_id"
        ]
        == str(admin.id)
    )

    get_response = await client.get(
        (
            "/api/v1/system-settings/"
            f"{setting_id}"
        )
    )

    assert get_response.status_code == 404

    list_response = await client.get(
        "/api/v1/system-settings",
        params={
            "system_id": str(
                system.id
            ),
            "include_deleted": True,
        },
    )

    assert list_response.status_code == 200

    deleted = next(
        item
        for item in list_response.json()
        if item["id"] == str(setting_id)
    )

    assert (
        deleted["deleted_at"]
        is not None
    )


async def test_non_admin_cannot_create_system_setting(
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
        "/api/v1/system-settings",
        json=build_setting_payload(
            system.id
        ),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator access required"
        )
    }


async def test_all_system_setting_mutations_require_admin():
    expected = {
        (
            "POST",
            "/system-settings",
        ),
        (
            "PATCH",
            (
                "/system-settings/"
                "{setting_id}"
            ),
        ),
        (
            "DELETE",
            (
                "/system-settings/"
                "{setting_id}"
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