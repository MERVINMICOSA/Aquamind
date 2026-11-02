from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from app.models.automation import AutomationRun


HISTORY_URL = "/api/v1/automation-runs/history"


@pytest_asyncio.fixture
async def history_data(
    client,
    test_session,
):
    response = await client.post(
        "/api/v1/systems",
        json={
            "name": "Automation run history test",
            "description": (
                "System created for bounded automation "
                "run history testing."
            ),
            "timezone": "UTC",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    system_id = response.json()["id"]

    rule_ids = []

    for index in range(3):
        response = await client.post(
            "/api/v1/automation-rules",
            json={
                "system_id": system_id,
                "name": (
                    f"Automation history rule {index}"
                ),
                "description": (
                    "Rule created for bounded automation "
                    "run history testing."
                ),
                "trigger_type": "schedule",
                "condition_definition": {
                    "schedule": "0 * * * *",
                },
                "action_definition": {
                    "action": "activate_actuator",
                    "actuator_type": "water_pump",
                    "value": 1.0,
                },
                "enabled": True,
                "priority": index,
                "cooldown_seconds": 0,
            },
        )

        assert response.status_code == 201

        rule_ids.append(
            UUID(
                response.json()["id"]
            )
        )

    base = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    runs = []

    for index in range(105):
        run = AutomationRun(
            id=UUID(int=index + 1),
            rule_id=rule_ids[0],
            started_at=(
                base
                + timedelta(
                    minutes=index // 4
                )
            ),
            completed_at=None,
            trigger_value=None,
            status="pending",
            result_summary=None,
            error_message=None,
        )

        runs.append(
            run
        )

        test_session.add(
            run
        )

    # A newer run from another rule must never consume a
    # history page slot for the requested rule.
    test_session.add(
        AutomationRun(
            rule_id=rule_ids[1],
            started_at=(
                base
                + timedelta(days=1)
            ),
            completed_at=(
                base
                + timedelta(
                    days=1,
                    seconds=5,
                )
            ),
            trigger_value=1.0,
            status="completed",
            result_summary=(
                "Other rule completed."
            ),
            error_message=None,
        )
    )

    await test_session.commit()

    ordered = sorted(
        runs,
        key=lambda run: (
            run.started_at,
            run.id,
        ),
        reverse=True,
    )

    return (
        rule_ids,
        [
            str(run.id)
            for run in ordered
        ],
    )


@pytest.mark.asyncio
async def test_history_defaults_contract_and_generic_list_unchanged(
    client,
    history_data,
):
    rule_ids, expected = history_data

    params = {
        "rule_id": str(
            rule_ids[0]
        )
    }

    response = await client.get(
        HISTORY_URL,
        params=params,
    )

    assert response.status_code == 200

    rows = response.json()

    assert [
        row["id"]
        for row in rows
    ] == expected[:50]

    assert set(
        rows[0]
    ) == {
        "id",
        "rule_id",
        "started_at",
        "completed_at",
        "trigger_value",
        "status",
        "result_summary",
        "error_message",
    }

    assert rows[0]["status"] == "pending"

    for field in (
        "completed_at",
        "trigger_value",
        "result_summary",
        "error_message",
    ):
        assert rows[0][field] is None

    generic = await client.get(
        "/api/v1/automation-runs",
        params=params,
    )

    assert generic.status_code == 200

    assert len(
        generic.json()
    ) == 105

    assert {
        row["id"]
        for row in generic.json()
    } == set(
        expected
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit",
    [
        1,
        51,
        100,
    ],
)
async def test_history_filter_order_and_pagination(
    client,
    history_data,
    limit,
):
    rule_ids, expected = history_data

    pages = []

    for offset in (
        0,
        limit,
    ):
        response = await client.get(
            HISTORY_URL,
            params={
                "rule_id": str(
                    rule_ids[0]
                ),
                "limit": limit,
                "offset": offset,
            },
        )

        assert response.status_code == 200

        rows = response.json()

        assert all(
            row["rule_id"]
            == str(rule_ids[0])
            for row in rows
        )

        ids = [
            row["id"]
            for row in rows
        ]

        assert ids == expected[
            offset:offset + limit
        ]

        pages.append(
            ids
        )

    assert set(
        pages[0]
    ).isdisjoint(
        pages[1]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {},
        {
            "rule_id": "invalid",
        },
        *[
            {
                "rule_id": str(
                    UUID(int=1)
                ),
                "limit": value,
            }
            for value in (
                0,
                -1,
                101,
                "invalid",
                "1.5",
            )
        ],
        *[
            {
                "rule_id": str(
                    UUID(int=1)
                ),
                "offset": value,
            }
            for value in (
                -1,
                "invalid",
                "1.5",
            )
        ],
    ],
)
async def test_history_invalid_queries(
    client,
    params,
):
    response = await client.get(
        HISTORY_URL,
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_history_missing_rule(
    client,
):
    response = await client.get(
        HISTORY_URL,
        params={
            "rule_id": str(
                uuid4()
            )
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": (
            "Automation rule not found"
        )
    }


@pytest.mark.asyncio
async def test_history_empty_and_exhausted_page(
    client,
    history_data,
):
    rule_ids, _ = history_data

    for rule_id, offset in (
        (
            rule_ids[2],
            0,
        ),
        (
            rule_ids[0],
            105,
        ),
    ):
        response = await client.get(
            HISTORY_URL,
            params={
                "rule_id": str(
                    rule_id
                ),
                "offset": offset,
            },
        )

        assert response.status_code == 200

        assert response.json() == []