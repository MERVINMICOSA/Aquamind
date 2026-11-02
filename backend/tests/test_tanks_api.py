import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tank_create_get_update_list_filter_delete_flow(
    client: AsyncClient,
):
    """
    Integration test for the tank lifecycle.

    Creates a parent aquaponics system, then creates, retrieves,
    updates, lists, filters, soft-deletes, and verifies removal
    of a tank.
    """

    # ---------------------------------------------------------
    # 1. Create parent aquaponics system
    # ---------------------------------------------------------
    system_payload = {
        "name": "Test Tank System",
        "description": "System created for tank API integration testing.",
        "timezone": "UTC",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/systems",
        json=system_payload,
    )

    assert response.status_code == 201

    system = response.json()

    assert system["name"] == "Test Tank System"
    assert system["timezone"] == "UTC"
    assert system["is_active"] is True

    system_id = system["id"]

    # ---------------------------------------------------------
    # 2. Create tank
    # ---------------------------------------------------------
    create_payload = {
        "system_id": system_id,
        "name": "Test Tilapia Tank",
        "capacity_liters": 1000.0,
        "species": "Tilapia",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/tanks",
        json=create_payload,
    )

    assert response.status_code == 201

    tank = response.json()

    assert tank["system_id"] == system_id
    assert tank["name"] == "Test Tilapia Tank"
    assert tank["capacity_liters"] == 1000.0
    assert tank["species"] == "Tilapia"
    assert tank["is_active"] is True

    tank_id = tank["id"]

    # ---------------------------------------------------------
    # 3. Get tank
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/tanks/{tank_id}"
    )

    assert response.status_code == 200

    fetched = response.json()

    assert fetched["id"] == tank_id
    assert fetched["system_id"] == system_id
    assert fetched["name"] == "Test Tilapia Tank"

    # ---------------------------------------------------------
    # 4. Update tank
    # ---------------------------------------------------------
    update_payload = {
        "name": "Updated Tilapia Tank",
        "capacity_liters": 1500.0,
        "species": "Nile Tilapia",
        "is_active": True,
    }

    response = await client.patch(
        f"/api/v1/tanks/{tank_id}",
        json=update_payload,
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["id"] == tank_id
    assert updated["name"] == "Updated Tilapia Tank"
    assert updated["capacity_liters"] == 1500.0
    assert updated["species"] == "Nile Tilapia"
    assert updated["is_active"] is True

    # ---------------------------------------------------------
    # 5. Tank should appear in normal listing
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/tanks"
    )

    assert response.status_code == 200

    tanks = response.json()

    assert any(
        item["id"] == tank_id
        for item in tanks
    )

    # ---------------------------------------------------------
    # 6. Filter tanks by system_id
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/tanks",
        params={"system_id": system_id},
    )

    assert response.status_code == 200

    filtered_tanks = response.json()

    assert filtered_tanks

    assert all(
        item["system_id"] == system_id
        for item in filtered_tanks
    )

    assert any(
        item["id"] == tank_id
        for item in filtered_tanks
    )

    # ---------------------------------------------------------
    # 7. Delete tank
    # ---------------------------------------------------------
    response = await client.delete(
        f"/api/v1/tanks/{tank_id}"
    )

    assert response.status_code == 204

    # ---------------------------------------------------------
    # 8. Deleted tank must no longer be accessible
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/tanks/{tank_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tank not found"

    # ---------------------------------------------------------
    # 9. Deleted tank must be excluded from normal listing
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/tanks"
    )

    assert response.status_code == 200

    active_tanks = response.json()

    assert all(
        item["id"] != tank_id
        for item in active_tanks
    )

    # ---------------------------------------------------------
    # 10. Updating a deleted tank must fail
    # ---------------------------------------------------------
    response = await client.patch(
        f"/api/v1/tanks/{tank_id}",
        json={
            "name": "Should Not Update",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tank not found"


@pytest.mark.asyncio
async def test_tank_requires_existing_system(
    client: AsyncClient,
):
    """
    A tank cannot be created when its parent system does not exist.
    """

    response = await client.post(
        "/api/v1/tanks",
        json={
            "system_id": "00000000-0000-0000-0000-000000000000",
            "name": "Orphan Tank",
            "capacity_liters": 500.0,
            "species": "Tilapia",
            "is_active": True,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Aquaponics system not found"