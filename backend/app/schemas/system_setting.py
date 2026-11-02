from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SystemSettingCreate(BaseModel):
    system_id: UUID
    setting_key: str = Field(
        min_length=1,
        max_length=150,
    )
    setting_value: str
    value_type: str = Field(
        min_length=1,
        max_length=32,
    )


class SystemSettingUpdate(BaseModel):
    setting_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    setting_value: str | None = None
    value_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=32,
    )


class SystemSettingResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    system_id: UUID
    setting_key: str
    setting_value: str
    value_type: str

    created_at: datetime
    updated_at: datetime
    updated_by_user_id: UUID | None
    deleted_at: datetime | None