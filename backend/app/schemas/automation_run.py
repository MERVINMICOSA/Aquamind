from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.enums import ExecutionStatus


class AutomationRunCreate(BaseModel):
    rule_id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    trigger_value: float | None = None
    status: ExecutionStatus
    result_summary: str | None = None
    error_message: str | None = None


class AutomationRunUpdate(BaseModel):
    completed_at: datetime | None = None
    trigger_value: float | None = None
    status: ExecutionStatus | None = None
    result_summary: str | None = None
    error_message: str | None = None


class AutomationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    started_at: datetime
    completed_at: datetime | None
    trigger_value: float | None
    status: ExecutionStatus
    result_summary: str | None
    error_message: str | None