from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.esp32_telemetry import (
    HistoryCorrectionInput, propose_history_correction,
)


def request(**changes):
    return HistoryCorrectionInput.model_validate({
        "field": "water_temp_c", "corrected_value": 27.5,
        "reason": "Reference comparison", "evidence": "Reference A",
        **changes,
    })


@pytest.mark.parametrize("changes", [
    {"field": "received_at"}, {"reason": " "}, {"evidence": ""},
    {"corrected_value": float("nan")}, {"corrected_value": True},
    {"extra": "unexpected"},
])
def test_invalid_correction_request(changes):
    with pytest.raises(ValidationError):
        request(**changes)


def context():
    system_id, packet_id = uuid4(), uuid4()
    item = SimpleNamespace(
        id=packet_id, system_id=system_id, device_id="test-device",
        sequence=1, uptime_ms=1000, received_at=datetime.now(timezone.utc),
        packet={"water_temp_c": 27.56, "ph": None, "ph_calibrated": False},
    )
    admin = SimpleNamespace(id=uuid4(), username="admin")
    session = Mock()
    session.get = AsyncMock(side_effect=[SimpleNamespace(deleted_at=None), item])
    session.commit = AsyncMock()
    async def refresh(log):
        log.id = uuid4()
    session.refresh = AsyncMock(side_effect=refresh)
    return system_id, packet_id, item, admin, session


@pytest.mark.asyncio
async def test_proposal_preserves_packet_and_records_evidence():
    system_id, packet_id, item, admin, session = context()
    original = item.packet.copy()
    result = await propose_history_correction(
        packet_id, system_id, request(), session, admin,
    )
    assert item.packet == original
    assert result["original_value"] == 27.56
    assert result["corrected_value"] == 27.5
    log = session.add.call_args.args[0]
    assert log.entity_id == packet_id
    assert log.user_id == admin.id
    assert log.new_value["evidence"] == "Reference A"
    assert log.source == "manual_validation"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [
    {"field": "ph", "corrected_value": 7.0},
    {"corrected_value": 1000},
    {"corrected_value": 27.56},
])
async def test_reject_missing_unchanged_or_out_of_bounds(changes):
    system_id, packet_id, item, admin, session = context()
    with pytest.raises(HTTPException) as error:
        await propose_history_correction(packet_id, system_id, request(**changes), session, admin)
    assert error.value.status_code == 422
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
