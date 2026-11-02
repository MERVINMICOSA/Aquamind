from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.models.actuators import Actuator, ActuatorEvent
from app.schemas.actuator_event import (
    ActuatorEventCreate,
    ActuatorEventResponse,
    ActuatorEventUpdate,
)

router = APIRouter(
    prefix="/actuator-events",
    tags=["Actuator Events"],
)


@router.post(
    "",
    response_model=ActuatorEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_actuator_event(
    payload: ActuatorEventCreate,
    session: AsyncSession = Depends(get_db_session),
) -> ActuatorEvent:
    actuator_stmt = select(Actuator).where(
        Actuator.id == payload.actuator_id,
        Actuator.deleted_at.is_(None),
    )

    actuator_result = await session.execute(actuator_stmt)
    actuator = actuator_result.scalar_one_or_none()

    if actuator is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator not found",
        )

    event = ActuatorEvent(
        actuator_id=payload.actuator_id,
        command_type=payload.command_type,
        requested_value=payload.requested_value,
        actual_value=payload.actual_value,
        started_at=payload.started_at,
        completed_at=payload.completed_at,
        duration_ms=payload.duration_ms,
        trigger_source=payload.trigger_source,
        status=payload.status,
        fault_code=payload.fault_code,
        error_message=payload.error_message,
    )

    session.add(event)
    await session.commit()
    await session.refresh(event)

    return event


@router.get(
    "",
    response_model=list[ActuatorEventResponse],
)
async def list_actuator_events(
    actuator_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> list[ActuatorEvent]:
    stmt = select(ActuatorEvent)

    if actuator_id is not None:
        stmt = stmt.where(ActuatorEvent.actuator_id == actuator_id)

    stmt = stmt.order_by(ActuatorEvent.created_at.desc())

    result = await session.execute(stmt)

    return list(result.scalars().all())


@router.get(
    "/history",
    response_model=list[ActuatorEventResponse],
)
async def list_actuator_event_history(
    actuator_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[ActuatorEvent]:
    """Return a bounded page of persisted events for one actuator."""
    actuator = await session.get(Actuator, actuator_id)

    if actuator is None or actuator.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator not found",
        )

    stmt = (
        select(ActuatorEvent)
        .where(ActuatorEvent.actuator_id == actuator_id)
        .order_by(
            ActuatorEvent.started_at.desc(),
            ActuatorEvent.created_at.desc(),
            ActuatorEvent.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{event_id}",
    response_model=ActuatorEventResponse,
)
async def get_actuator_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ActuatorEvent:
    stmt = select(ActuatorEvent).where(
        ActuatorEvent.id == event_id,
    )

    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator event not found",
        )

    return event


@router.patch(
    "/{event_id}",
    response_model=ActuatorEventResponse,
)
async def update_actuator_event(
    event_id: UUID,
    payload: ActuatorEventUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> ActuatorEvent:
    stmt = select(ActuatorEvent).where(
        ActuatorEvent.id == event_id,
    )

    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator event not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(event, field, value)

    await session.commit()
    await session.refresh(event)

    return event
