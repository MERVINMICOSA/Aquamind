from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from app.api.dependencies import get_current_user
from app.main import app
from app.models.alerts import Alert
from app.models.system import AquaponicsSystem


HISTORY_URL = "/api/v1/alerts/history"
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def history_data(test_session):
    systems = [
        AquaponicsSystem(name=f"Alert history {index}", timezone="UTC", is_active=index != 0)
        for index in range(3)
    ]
    test_session.add_all(systems)
    await test_session.flush()
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    statuses = ("active", "acknowledged", "resolved")
    alerts = []
    for index in range(105):
        alert = Alert(
            id=UUID(int=index + 1),
            system_id=systems[0].id,
            alert_type="test",
            severity="warning",
            message=f"Persisted test alert {index}",
            trigger_value=0,
            status=statuses[index % 3],
            created_at=base + timedelta(minutes=index // 3),
        )
        alerts.append(alert)
        test_session.add(alert)
    # A newer alert from another system must not consume a page slot.
    test_session.add(Alert(
        system_id=systems[1].id,
        alert_type="test",
        severity="warning",
        message="Other system",
        status="active",
        created_at=base + timedelta(days=1),
    ))
    await test_session.commit()
    expected = [str(alert.id) for alert in reversed(alerts)]
    return systems, expected


async def test_history_defaults_response_and_generic_list_preserved(client, history_data):
    systems, expected = history_data
    params = {"system_id": str(systems[0].id)}
    response = await client.get(HISTORY_URL, params=params)
    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == expected[:50]
    assert {row["status"] for row in rows} == {"active", "acknowledged", "resolved"}
    assert set(rows[0]) == {
        "id", "system_id", "sensor_id", "actuator_id", "alert_type", "severity",
        "message", "trigger_value", "threshold_id", "status", "created_at",
        "acknowledged_at", "acknowledged_by_user_id", "resolved_at", "resolution_reason",
    }
    assert rows[0]["trigger_value"] == 0
    for field in ("sensor_id", "actuator_id", "threshold_id", "acknowledged_at",
                  "acknowledged_by_user_id", "resolved_at", "resolution_reason"):
        assert rows[0][field] is None

    generic = await client.get("/api/v1/alerts", params=params)
    assert generic.status_code == 200
    assert len(generic.json()) == 105
    assert {row["id"] for row in generic.json()} == set(expected)


@pytest.mark.parametrize("limit", [1, 51, 100])
async def test_history_system_filter_order_and_pagination(client, history_data, limit):
    systems, expected = history_data
    pages = []
    for offset in (0, limit):
        response = await client.get(HISTORY_URL, params={
            "system_id": str(systems[0].id), "limit": limit, "offset": offset,
        })
        assert response.status_code == 200
        rows = response.json()
        assert all(row["system_id"] == str(systems[0].id) for row in rows)
        ids = [row["id"] for row in rows]
        assert ids == expected[offset:offset + limit]
        pages.append(ids)
    assert set(pages[0]).isdisjoint(pages[1])


@pytest.mark.parametrize("params", [
    {},
    {"system_id": "invalid"},
    *[{"system_id": str(UUID(int=1)), "limit": value}
      for value in (0, -1, 101, "invalid", "1.5")],
    *[{"system_id": str(UUID(int=1)), "offset": value}
      for value in (-1, "invalid", "1.5")],
])
async def test_history_invalid_queries(client, params):
    response = await client.get(HISTORY_URL, params=params)
    assert response.status_code == 422


async def test_history_missing_and_soft_deleted_system(client, history_data, test_session):
    systems, _ = history_data
    systems[0].deleted_at = datetime.now(timezone.utc)
    await test_session.commit()
    for system_id in (uuid4(), systems[0].id):
        response = await client.get(HISTORY_URL, params={"system_id": str(system_id)})
        assert response.status_code == 404
        assert response.json() == {"detail": "Aquaponics system not found"}


async def test_history_empty_and_exhausted_page(client, history_data):
    systems, _ = history_data
    for system_id, offset in ((systems[2].id, 0), (systems[0].id, 105)):
        response = await client.get(HISTORY_URL, params={"system_id": str(system_id), "offset": offset})
        assert response.status_code == 200
        assert response.json() == []


async def test_history_requires_authentication(client):
    override = app.dependency_overrides.pop(get_current_user)
    try:
        response = await client.get(HISTORY_URL, params={"system_id": str(uuid4())})
        assert response.status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = override
