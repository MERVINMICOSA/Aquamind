import pytest


pytestmark = pytest.mark.asyncio


async def test_system_setting_crud(client):
    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "System Settings Test",
            "description": (
                "System used for settings API testing."
            ),
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert system_response.status_code == 201

    system = system_response.json()

    create_response = await client.post(
        "/api/v1/system-settings",
        json={
            "system_id": system["id"],
            "setting_key": "water_temperature_target",
            "setting_value": "26.5",
            "value_type": "float",
        },
    )

    assert create_response.status_code == 201

    setting = create_response.json()

    assert setting["system_id"] == system["id"]
    assert (
        setting["setting_key"]
        == "water_temperature_target"
    )
    assert setting["setting_value"] == "26.5"
    assert setting["value_type"] == "float"
    assert setting["updated_by_user_id"] is not None
    assert setting["deleted_at"] is None

    setting_id = setting["id"]

    get_response = await client.get(
        f"/api/v1/system-settings/{setting_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == setting_id

    list_response = await client.get(
        "/api/v1/system-settings",
        params={
            "system_id": system["id"],
            "setting_key": (
                "water_temperature_target"
            ),
        },
    )

    assert list_response.status_code == 200

    settings = list_response.json()

    assert len(settings) == 1
    assert settings[0]["id"] == setting_id

    update_response = await client.patch(
        f"/api/v1/system-settings/{setting_id}",
        json={
            "setting_value": "27.0",
            "value_type": "float",
        },
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["setting_value"] == "27.0"
    assert updated["value_type"] == "float"

    delete_response = await client.delete(
        f"/api/v1/system-settings/{setting_id}"
    )

    assert delete_response.status_code == 204

    missing_response = await client.get(
        f"/api/v1/system-settings/{setting_id}"
    )

    assert missing_response.status_code == 404
    assert (
        missing_response.json()["detail"]
        == "System setting not found"
    )

    normal_list_response = await client.get(
        "/api/v1/system-settings",
        params={
            "system_id": system["id"],
        },
    )

    assert normal_list_response.status_code == 200
    assert normal_list_response.json() == []

    deleted_list_response = await client.get(
        "/api/v1/system-settings",
        params={
            "system_id": system["id"],
            "include_deleted": True,
        },
    )

    assert deleted_list_response.status_code == 200

    deleted_settings = deleted_list_response.json()

    assert len(deleted_settings) == 1
    assert deleted_settings[0]["id"] == setting_id
    assert (
        deleted_settings[0]["deleted_at"]
        is not None
    )


async def test_system_setting_validation(client):
    missing_system_response = await client.post(
        "/api/v1/system-settings",
        json={
            "system_id": (
                "00000000-0000-0000-0000-000000000000"
            ),
            "setting_key": "invalid_setting",
            "setting_value": "1",
            "value_type": "integer",
        },
    )

    assert missing_system_response.status_code == 404
    assert (
        missing_system_response.json()["detail"]
        == "Aquaponics system not found"
    )

    system_response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Duplicate Setting Test",
            "description": None,
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert system_response.status_code == 201

    system_id = system_response.json()["id"]

    payload = {
        "system_id": system_id,
        "setting_key": "refill_enabled",
        "setting_value": "true",
        "value_type": "boolean",
    }

    first_response = await client.post(
        "/api/v1/system-settings",
        json=payload,
    )

    assert first_response.status_code == 201

    duplicate_response = await client.post(
        "/api/v1/system-settings",
        json=payload,
    )

    assert duplicate_response.status_code == 409
    assert (
        duplicate_response.json()["detail"]
        == "System setting with this key already exists"
    )