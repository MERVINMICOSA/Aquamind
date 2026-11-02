from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.db.enums import (
    ActuatorCommandType,
    ActuatorType,
    ExecutionStatus,
)


@dataclass(frozen=True, slots=True)
class ActuatorExecutionCommand:
    actuator_id: UUID
    actuator_type: ActuatorType
    hardware_identifier: str | None

    command_type: ActuatorCommandType
    requested_value: float


@dataclass(frozen=True, slots=True)
class ActuatorExecutionResult:
    status: ExecutionStatus
    completed_at: datetime

    actual_value: float | None = None

    result_summary: str | None = None

    fault_code: str | None = None
    error_message: str | None = None


class ActuatorExecutor(Protocol):
    async def execute(
        self,
        command: ActuatorExecutionCommand,
    ) -> ActuatorExecutionResult:
        ...