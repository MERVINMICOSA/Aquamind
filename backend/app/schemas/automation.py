from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import AutomationTriggerType, ExecutionStatus


class AutomationRuleCreate(BaseModel):
    system_id: UUID

    name: str = Field(
        min_length=1,
        max_length=150,
    )

    description: str | None = None

    trigger_type: AutomationTriggerType

    condition_definition: dict

    action_definition: dict

    enabled: bool = True

    priority: int = 0

    cooldown_seconds: int = Field(
        default=0,
        ge=0,
    )


class AutomationRuleUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )

    description: str | None = None

    trigger_type: AutomationTriggerType | None = None

    condition_definition: dict | None = None

    action_definition: dict | None = None

    enabled: bool | None = None

    priority: int | None = None

    cooldown_seconds: int | None = Field(
        default=None,
        ge=0,
    )


class AutomationRuleResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    system_id: UUID

    name: str

    description: str | None

    trigger_type: AutomationTriggerType

    condition_definition: dict

    action_definition: dict

    enabled: bool

    priority: int

    cooldown_seconds: int

    created_at: datetime

    updated_at: datetime


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
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    rule_id: UUID

    started_at: datetime

    completed_at: datetime | None

    trigger_value: float | None

    status: ExecutionStatus

    result_summary: str | None

    error_message: str | None