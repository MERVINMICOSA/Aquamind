from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import ReadingQuality, ReadingSource


class SensorReadingCreate(BaseModel):
    sensor_id: UUID
    recorded_at: datetime
    value_numeric: float
    unit: str = Field(min_length=1, max_length=32)
    quality_status: ReadingQuality = ReadingQuality.GOOD
    source: ReadingSource = ReadingSource.SIMULATOR
    sequence_number: int | None = Field(default=None, ge=0)


class SensorReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sensor_id: UUID
    recorded_at: datetime
    value_numeric: float
    unit: str
    quality_status: ReadingQuality
    source: ReadingSource
    sequence_number: int | None
    created_at: datetime
