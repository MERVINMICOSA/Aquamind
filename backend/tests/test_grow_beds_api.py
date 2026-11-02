import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_grow_bed_create_get_update_delete_flow(
    client: AsyncClient,
):
    """
    Integration test for the grow bed lifecycle.

    Creates an aquaponics system first because grow beds belong
    to a system through a foreign-key relationship.

    Then creates, retrieves, updates, lists, filters, and
    soft-deletes the grow bed.
    """

    # ---------------------------------------------------------
    # 1. Create parent aquaponics system
    # ---------------------------------------------------------
    system_payload = {
        "name": "Test Grow Bed System",
        "description": "System created for grow bed API integration testing.",
        "timezone": "UTC",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/systems",
        json=system_payload,
    )

    print("GROW BED RESPONSE:", response.status_code, response.json())
    assert response.status_code == 201

    system = response.json()

    assert system["name"] == "Test Grow Bed System"
    assert system["timezone"] == "UTC"
    assert system["is_active"] is True

    system_id = system["id"]

    # ---------------------------------------------------------
    # 2. Create grow bed
    # ---------------------------------------------------------
    create_payload = {
        "system_id": system_id,
        "name": "Test Lettuce Grow Bed",
        "crop_type": "Lettuce",
        "capacity_description": "12 planting channels",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/grow-beds",
        json=create_payload,
    )

    print("GROW BED CREATE RESPONSE:", response.status_code, response.json())
    assert response.status_code == 201

    grow_bed = response.json()

    assert grow_bed["system_id"] == system_id
    assert grow_bed["name"] == "Test Lettuce Grow Bed"
    assert grow_bed["crop_type"] == "Lettuce"
    assert grow_bed["capacity_description"] == "12 planting channels"
    assert grow_bed["is_active"] is True

    grow_bed_id = grow_bed["id"]

    # ---------------------------------------------------------
    # 3. Get grow bed
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/grow-beds/{grow_bed_id}"
    )

    assert response.status_code == 200

    fetched = response.json()

    assert fetched["id"] == grow_bed_id
    assert fetched["name"] == "Test Lettuce Grow Bed"

    # ---------------------------------------------------------
    # 4. Update grow bed
    # ---------------------------------------------------------
    update_payload = {
        "name": "Updated Lettuce Grow Bed",
        "crop_type": "Basil",
        "capacity_description": "16 planting channels",
        "is_active": True,
    }

    response = await client.patch(
        f"/api/v1/grow-beds/{grow_bed_id}",
        json=update_payload,
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["id"] == grow_bed_id
    assert updated["name"] == "Updated Lettuce Grow Bed"
    assert updated["crop_type"] == "Basil"
    assert updated["capacity_description"] == "16 planting channels"
    assert updated["is_active"] is True

    # ---------------------------------------------------------
    # 5. Grow bed should appear in normal listing
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/grow-beds"
    )

    assert response.status_code == 200

    grow_beds = response.json()

    assert any(
        item["id"] == grow_bed_id
        for item in grow_beds
    )

    # ---------------------------------------------------------
    # 6. Filter grow beds by system_id
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/grow-beds"
        f"?system_id={system_id}"
    )

    assert response.status_code == 200

    filtered_grow_beds = response.json()

    assert filtered_grow_beds

    assert all(
        item["system_id"] == system_id
        for item in filtered_grow_beds
    )

    assert any(
        item["id"] == grow_bed_id
        for item in filtered_grow_beds
    )

    # ---------------------------------------------------------
    # 7. Delete grow bed
    # ---------------------------------------------------------
    response = await client.delete(
        f"/api/v1/grow-beds/{grow_bed_id}"
    )

    assert response.status_code == 204

    # ---------------------------------------------------------
    # 8. Deleted grow bed must no longer be accessible
    # ---------------------------------------------------------
    response = await client.get(
        f"/api/v1/grow-beds/{grow_bed_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Grow bed not found"

    # ---------------------------------------------------------
    # 9. Deleted grow bed must be excluded from listing
    # ---------------------------------------------------------
    response = await client.get(
        "/api/v1/grow-beds"
    )

    assert response.status_code == 200

    active_grow_beds = response.json()

    assert all(
        item["id"] != grow_bed_id
        for item in active_grow_beds
    )

    # ---------------------------------------------------------
    # 10. Updating a deleted grow bed must fail
    # ---------------------------------------------------------
    response = await client.patch(
        f"/api/v1/grow-beds/{grow_bed_id}",
        json={
            "name": "Should Not Update",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Grow bed not found"


@pytest.mark.asyncio
async def test_create_grow_bed_requires_existing_system(
    client: AsyncClient,
):
    """
    A grow bed cannot be created for a system that does not exist.
    """

    payload = {
        "system_id": "00000000-0000-0000-0000-000000000001",
        "name": "Invalid Grow Bed",
        "crop_type": "Lettuce",
        "capacity_description": "Test",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/grow-beds",
        json=payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Aquaponics system not found"