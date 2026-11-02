import pytest
from httpx import AsyncClient
from app.main import app


print("\n=== EFFECTIVE ROUTES ===")
for route in app.routes:
    if hasattr(route, "routes"):
        for subroute in route.routes:
            print(
                "ROUTE:",
                getattr(subroute, "path", None),
                getattr(subroute, "methods", None),
            )
    elif hasattr(route, "path"):
        print(
            "ROUTE:",
            route.path,
            getattr(route, "methods", None),
        )


@pytest.mark.asyncio
async def test_alert_create_get_list_and_filter_flow(
    client: AsyncClient,
):
    """
    Integration test for the alert API lifecycle.

    Creates the required system and sensor, creates an alert,
    retrieves it, lists it, filters it, updates it, and deletes it.
    """

    # ---------------------------------------------------------
    # 1. Create system
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Alert API Test System",
            "description": "System for alert API testing.",
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system = response.json()
    system_id = system["id"]

    assert system["name"] == "Alert API Test System"
    assert system["timezone"] == "UTC"
    assert system["is_active"] is True

    # ---------------------------------------------------------
    # 2. Create sensor
    # ---------------------------------------------------------

    response = await client.post(
        "/api/v1/sensors",
        json={
            "system_id": system_id,
            "name": "Alert API pH Sensor",
            "sensor_type": "ph",
            "measurement_type": "ph",
            "location_type": "tank",
            "location_id": None,
            "unit": "pH",
            "hardware_identifier": "PH-ALERT-API-001",
            "is_simulated": True,
            "is_enabled": True,
            "sampling_interval_seconds": 10,
            "calibration_status": "pending",
        },
    )

    assert response.status_code == 201

    sensor = response.json()
    sensor_id = sensor["id"]

    # ---------------------------------------------------------
    # 3. Create alert
    # ---------------------------------------------------------

    alert_payload = {
        "system_id": system_id,
        "sensor_id": sensor_id,
        "actuator_id": None,
        "alert_type": "ph",
        "severity": "warning",
        "message": "pH level is outside the normal range.",
        "trigger_value": 6.3,
        "threshold_id": None,
        "status": "active",
    }

    response = await client.post(
        "/api/v1/alerts",
        json=alert_payload,
    )

    print("ALERT RESPONSE STATUS:", response.status_code)
    print("ALERT RESPONSE BODY:", response.text)

    assert response.status_code == 201

    alert = response.json()
    alert_id = alert["id"]

    assert alert["system_id"] == system_id
    assert alert["sensor_id"] == sensor_id
    assert alert["actuator_id"] is None
    assert alert["alert_type"] == "ph"
    assert alert["severity"] == "warning"
    assert alert["message"] == (
        "pH level is outside the normal range."
    )
    assert alert["trigger_value"] == 6.3
    assert alert["status"] == "active"
    assert alert["acknowledged_at"] is None
    assert alert["resolved_at"] is None

    # ---------------------------------------------------------
    # 4. Get alert
    # ---------------------------------------------------------

    response = await client.get(
        f"/api/v1/alerts/{alert_id}"
    )

    assert response.status_code == 200

    fetched = response.json()

    assert fetched["id"] == alert_id
    assert fetched["system_id"] == system_id
    assert fetched["sensor_id"] == sensor_id
    assert fetched["severity"] == "warning"
    assert fetched["status"] == "active"

    # ---------------------------------------------------------
    # 5. List alerts
    # ---------------------------------------------------------

    response = await client.get(
        "/api/v1/alerts"
    )

    assert response.status_code == 200

    alerts = response.json()

    assert any(
        item["id"] == alert_id
        for item in alerts
    )

    # ---------------------------------------------------------
    # 6. Filter by system_id
    # ---------------------------------------------------------

    response = await client.get(
        "/api/v1/alerts",
        params={"system_id": system_id},
    )

    assert response.status_code == 200

    system_alerts = response.json()

    assert system_alerts

    assert all(
        item["system_id"] == system_id
        for item in system_alerts
    )

    assert any(
        item["id"] == alert_id
        for item in system_alerts
    )

    # ---------------------------------------------------------
    # 7. Filter by sensor_id
    # ---------------------------------------------------------

    response = await client.get(
        "/api/v1/alerts",
        params={"sensor_id": sensor_id},
    )

    assert response.status_code == 200

    sensor_alerts = response.json()

    assert sensor_alerts

    assert all(
        item["sensor_id"] == sensor_id
        for item in sensor_alerts
    )

    # ---------------------------------------------------------
    # 8. Filter by status
    # ---------------------------------------------------------

    response = await client.get(
        "/api/v1/alerts",
        params={"alert_status": "active"},
    )

    assert response.status_code == 200

    active_alerts = response.json()

    assert any(
        item["id"] == alert_id
        for item in active_alerts
    )

    assert all(
        item["status"] == "active"
        for item in active_alerts
    )

    # ---------------------------------------------------------
    # 9. Acknowledge alert
    # ---------------------------------------------------------

    response = await client.patch(
        f"/api/v1/alerts/{alert_id}",
        json={
            "status": "acknowledged",
        },
    )

    assert response.status_code == 200

    acknowledged = response.json()

    assert acknowledged["id"] == alert_id
    assert acknowledged["status"] == "acknowledged"
    assert acknowledged["acknowledged_at"] is not None

    # ---------------------------------------------------------
    # 10. Resolve alert
    # ---------------------------------------------------------

    response = await client.patch(
        f"/api/v1/alerts/{alert_id}",
        json={
            "status": "resolved",
            "resolution_reason": "pH returned to normal range.",
        },
    )

    assert response.status_code == 200

    resolved = response.json()

    assert resolved["id"] == alert_id
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None
    assert resolved["resolution_reason"] == (
        "pH returned to normal range."
    )

    # ---------------------------------------------------------
    # 11. Delete alert
    # ---------------------------------------------------------

    response = await client.delete(
        f"/api/v1/alerts/{alert_id}"
    )

    assert response.status_code == 204

    # ---------------------------------------------------------
    # 12. Verify alert no longer exists
    # ---------------------------------------------------------

    response = await client.get(
        f"/api/v1/alerts/{alert_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"


@pytest.mark.asyncio
async def test_get_nonexistent_alert_returns_404(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/alerts/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"


@pytest.mark.asyncio
async def test_create_alert_with_nonexistent_system_returns_404(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/alerts",
        json={
            "system_id": "00000000-0000-0000-0000-000000000000",
            "sensor_id": None,
            "actuator_id": None,
            "alert_type": "ph",
            "severity": "warning",
            "message": "Test alert",
            "trigger_value": 6.3,
            "threshold_id": None,
            "status": "active",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Aquaponics system not found"
    )


@pytest.mark.asyncio
async def test_delete_nonexistent_alert_returns_404(
    client: AsyncClient,
):
    response = await client.delete(
        "/api/v1/alerts/"
        "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"