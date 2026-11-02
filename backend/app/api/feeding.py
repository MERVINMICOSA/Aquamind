from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from enum import Enum

from app.api.dependencies import (
    get_current_user,
    get_db_session,
    require_admin,
)
from app.models.actuators import Actuator, ActuatorEvent
from app.models.feeding import (
    FeedingEvent,
    FeedingSchedule,
    FeederCalibration,
    FishPopulationRecord,
)
from app.models.system import (
    AquaponicsSystem,
    Tank,
    User,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)
from app.schemas.feeding import (
    FeedingEventCreate,
    FeedingEventResponse,
    FeedingEventUpdate,
    FeedingScheduleCreate,
    FeedingScheduleResponse,
    FeedingScheduleUpdate,
    FeederCalibrationCreate,
    FeederCalibrationResponse,
    FeederCalibrationUpdate,
    FishPopulationRecordCreate,
    FishPopulationRecordResponse,
    FishPopulationRecordUpdate,
)


router = APIRouter(
    prefix="/feeding",
    tags=["feeding"],
)

def _audit_value(
    value,
):
    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {
            str(key): _audit_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _audit_value(item)
            for item in value
        ]

    return value


def _feeding_schedule_audit_snapshot(
    schedule: FeedingSchedule,
) -> dict:
    return {
        "system_id": _audit_value(
            schedule.system_id
        ),
        "actuator_id": _audit_value(
            schedule.actuator_id
        ),
        "name": _audit_value(
            schedule.name
        ),
        "schedule_expression": _audit_value(
            schedule.schedule_expression
        ),
        "enabled": _audit_value(
            schedule.enabled
        ),
        "max_per_feed_grams": _audit_value(
            schedule.max_per_feed_grams
        ),
    }

def _feeder_calibration_audit_snapshot(
    calibration: FeederCalibration,
) -> dict:
    return {
        "actuator_id": _audit_value(
            calibration.actuator_id
        ),
        "run_count": _audit_value(
            calibration.run_count
        ),
        "measured_seconds": _audit_value(
            calibration.measured_seconds
        ),
        "measured_grams": _audit_value(
            calibration.measured_grams
        ),
        "grams_per_second": _audit_value(
            calibration.grams_per_second
        ),
        "calibration_method": _audit_value(
            calibration.calibration_method
        ),
        "performed_at": _audit_value(
            calibration.performed_at
        ),
        "verified_by_user_id": _audit_value(
            calibration.verified_by_user_id
        ),
        "notes": _audit_value(
            calibration.notes
        ),
    }

def _fish_population_record_audit_snapshot(
    record: FishPopulationRecord,
) -> dict:
    return {
        "tank_id": _audit_value(
            record.tank_id
        ),
        "species": _audit_value(
            record.species
        ),
        "count": _audit_value(
            record.count
        ),
        "estimated_biomass_grams": _audit_value(
            record.estimated_biomass_grams
        ),
        "effective_at": _audit_value(
            record.effective_at
        ),
        "recorded_by_user_id": _audit_value(
            record.recorded_by_user_id
        ),
        "notes": _audit_value(
            record.notes
        ),
    }

def _feeding_event_audit_snapshot(
    event: FeedingEvent,
) -> dict:
    return {
        "schedule_id": _audit_value(
            event.schedule_id
        ),
        "actuator_event_id": _audit_value(
            event.actuator_event_id
        ),
        "tank_id": _audit_value(
            event.tank_id
        ),
        "amount_grams": _audit_value(
            event.amount_grams
        ),
        "duration_seconds": _audit_value(
            event.duration_seconds
        ),
        "calculated_from_biomass": _audit_value(
            event.calculated_from_biomass
        ),
        "calibration_id": _audit_value(
            event.calibration_id
        ),
        "executed_at": _audit_value(
            event.executed_at
        ),
        "status": _audit_value(
            event.status
        ),
        "notes": _audit_value(
            event.notes
        ),
    }

# ============================================================
# Feeding Schedules
# ============================================================

@router.get(
    "/schedules",
    response_model=list[FeedingScheduleResponse],
)
async def list_feeding_schedules(
    system_id: UUID | None = None,
    actuator_id: UUID | None = None,
    enabled: bool | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    query = (
        select(FeedingSchedule)
        .order_by(FeedingSchedule.name)
    )

    if system_id is not None:
        query = query.where(
            FeedingSchedule.system_id == system_id
        )

    if actuator_id is not None:
        query = query.where(
            FeedingSchedule.actuator_id == actuator_id
        )

    if enabled is not None:
        query = query.where(
            FeedingSchedule.enabled == enabled
        )

    result = await session.execute(query)

    return result.scalars().all()


@router.get(
    "/schedules/{schedule_id}",
    response_model=FeedingScheduleResponse,
)
async def get_feeding_schedule(
    schedule_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    schedule = await session.get(
        FeedingSchedule,
        schedule_id,
    )

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeding schedule not found",
        )

    return schedule


@router.post(
    "/schedules",
    response_model=FeedingScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feeding_schedule(
    payload: FeedingScheduleCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    system = await session.get(
        AquaponicsSystem,
        payload.system_id,
    )

    if (
        system is None
        or system.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquaponics system not found",
        )

    actuator = await session.get(
        Actuator,
        payload.actuator_id,
    )

    if (
        actuator is None
        or actuator.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator not found",
        )

    if (
        actuator.system_id
        != payload.system_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Actuator does not belong "
                "to the specified system"
            ),
        )

    schedule = FeedingSchedule(
        system_id=payload.system_id,
        actuator_id=payload.actuator_id,
        name=payload.name,
        schedule_expression=(
            payload.schedule_expression
        ),
        enabled=payload.enabled,
        max_per_feed_grams=(
            payload.max_per_feed_grams
        ),
    )

    session.add(
        schedule
    )

    await session.commit()
    await session.refresh(
        schedule
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="feeding_schedule",
        entity_id=schedule.id,
        new_value=(
            _feeding_schedule_audit_snapshot(
                schedule
            )
        ),
    )

    return schedule


@router.patch(
    "/schedules/{schedule_id}",
    response_model=FeedingScheduleResponse,
)
async def update_feeding_schedule(
    schedule_id: UUID,
    payload: FeedingScheduleUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    schedule = await session.get(
        FeedingSchedule,
        schedule_id,
    )

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeding schedule not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    if "actuator_id" in updates:
        actuator = await session.get(
            Actuator,
            updates["actuator_id"],
        )

        if (
            actuator is None
            or actuator.deleted_at is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Actuator not found",
            )

        if (
            actuator.system_id
            != schedule.system_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Actuator does not belong "
                    "to the schedule system"
                ),
            )

    old_value = {
        field: _audit_value(
            getattr(
                schedule,
                field,
            )
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            schedule,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        schedule
    )

    new_value = {
        field: _audit_value(
            getattr(
                schedule,
                field,
            )
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="feeding_schedule",
        entity_id=schedule.id,
        old_value=old_value,
        new_value=new_value,
    )

    return schedule


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_feeding_schedule(
    schedule_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    schedule = await session.get(
        FeedingSchedule,
        schedule_id,
    )

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeding schedule not found",
        )

    old_value = (
        _feeding_schedule_audit_snapshot(
            schedule
        )
    )

    entity_id = schedule.id

    await session.delete(
        schedule
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="feeding_schedule",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )


# ============================================================
# Feeder Calibrations
# ============================================================

@router.get(
    "/calibrations",
    response_model=list[FeederCalibrationResponse],
)
async def list_feeder_calibrations(
    actuator_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    query = (
        select(FeederCalibration)
        .order_by(FeederCalibration.performed_at.desc())
    )

    if actuator_id is not None:
        query = query.where(
            FeederCalibration.actuator_id == actuator_id
        )

    result = await session.execute(query)

    return result.scalars().all()

@router.get(
    "/calibrations/history",
    response_model=list[FeederCalibrationResponse],
)
async def get_feeder_calibration_history(
    actuator_id: UUID,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> list[FeederCalibration]:
    actuator = await session.get(
        Actuator,
        actuator_id,
    )

    if (
        actuator is None
        or actuator.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator not found",
        )

    query = (
        select(FeederCalibration)
        .where(
            FeederCalibration.actuator_id
            == actuator_id
        )
        .order_by(
            FeederCalibration.performed_at.desc(),
            FeederCalibration.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(
        query
    )

    return list(
        result.scalars().all()
    )

@router.get(
    "/calibrations/{calibration_id}",
    response_model=FeederCalibrationResponse,
)
async def get_feeder_calibration(
    calibration_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    calibration = await session.get(
        FeederCalibration,
        calibration_id,
    )

    if calibration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeder calibration not found",
        )

    return calibration


@router.post(
    "/calibrations",
    response_model=FeederCalibrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feeder_calibration(
    payload: FeederCalibrationCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    actuator = await session.get(
        Actuator,
        payload.actuator_id,
    )

    if (
        actuator is None
        or actuator.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator not found",
        )

    verified_by_user_id = None

    if payload.verified_by_user_id is not None:
        verified_by_user_id = current_user.id

    calibration = FeederCalibration(
        actuator_id=payload.actuator_id,
        run_count=payload.run_count,
        measured_seconds=(
            payload.measured_seconds
        ),
        measured_grams=(
            payload.measured_grams
        ),
        grams_per_second=(
            payload.grams_per_second
        ),
        calibration_method=(
            payload.calibration_method
        ),
        performed_at=payload.performed_at,
        verified_by_user_id=(
            verified_by_user_id
        ),
        notes=payload.notes,
    )

    session.add(
        calibration
    )

    await session.commit()
    await session.refresh(
        calibration
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="feeder_calibration",
        entity_id=calibration.id,
        new_value=(
            _feeder_calibration_audit_snapshot(
                calibration
            )
        ),
    )

    return calibration


@router.patch(
    "/calibrations/{calibration_id}",
    response_model=FeederCalibrationResponse,
)
async def update_feeder_calibration(
    calibration_id: UUID,
    payload: FeederCalibrationUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    calibration = await session.get(
        FeederCalibration,
        calibration_id,
    )

    if calibration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeder calibration not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    # A client may request verification, but it cannot
    # choose which user performed that verification.
    #
    # Explicit None remains meaningful: it clears
    # verification.
    if (
        "verified_by_user_id" in updates
        and updates["verified_by_user_id"]
        is not None
    ):
        updates["verified_by_user_id"] = (
            current_user.id
        )

    old_value = {
        field: _audit_value(
            getattr(
                calibration,
                field,
            )
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            calibration,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        calibration
    )

    new_value = {
        field: _audit_value(
            getattr(
                calibration,
                field,
            )
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="feeder_calibration",
        entity_id=calibration.id,
        old_value=old_value,
        new_value=new_value,
    )

    return calibration


@router.delete(
    "/calibrations/{calibration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_feeder_calibration(
    calibration_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    calibration = await session.get(
        FeederCalibration,
        calibration_id,
    )

    if calibration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeder calibration not found",
        )

    old_value = (
        _feeder_calibration_audit_snapshot(
            calibration
        )
    )

    entity_id = calibration.id

    await session.delete(
        calibration
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="feeder_calibration",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )


# ============================================================
# Fish Population Records
# ============================================================

@router.get(
    "/population",
    response_model=list[FishPopulationRecordResponse],
)
async def list_population_records(
    tank_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    query = (
        select(FishPopulationRecord)
        .order_by(FishPopulationRecord.effective_at.desc())
    )

    if tank_id is not None:
        query = query.where(
            FishPopulationRecord.tank_id == tank_id
        )

    result = await session.execute(query)

    return result.scalars().all()

@router.get(
    "/population/history",
    response_model=list[FishPopulationRecordResponse],
)
async def get_fish_population_history(
    tank_id: UUID,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> list[FishPopulationRecord]:
    tank = await session.get(
        Tank,
        tank_id,
    )

    if (
        tank is None
        or tank.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tank not found",
        )

    query = (
        select(FishPopulationRecord)
        .where(
            FishPopulationRecord.tank_id
            == tank_id
        )
        .order_by(
            FishPopulationRecord.effective_at.desc(),
            FishPopulationRecord.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(
        query
    )

    return list(
        result.scalars().all()
    )

@router.get(
    "/population/{record_id}",
    response_model=FishPopulationRecordResponse,
)
async def get_population_record(
    record_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    record = await session.get(
        FishPopulationRecord,
        record_id,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fish population record not found",
        )

    return record


@router.post(
    "/population",
    response_model=FishPopulationRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_population_record(
    payload: FishPopulationRecordCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    tank = await session.get(
        Tank,
        payload.tank_id,
    )

    if (
        tank is None
        or tank.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tank not found",
        )

    record = FishPopulationRecord(
        tank_id=payload.tank_id,
        species=payload.species,
        count=payload.count,
        estimated_biomass_grams=(
            payload.estimated_biomass_grams
        ),
        effective_at=payload.effective_at,

        # Recorder identity is authoritative from
        # authentication, never from the request.
        recorded_by_user_id=current_user.id,

        notes=payload.notes,
    )

    session.add(
        record
    )

    await session.commit()
    await session.refresh(
        record
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="fish_population_record",
        entity_id=record.id,
        new_value=(
            _fish_population_record_audit_snapshot(
                record
            )
        ),
    )

    return record


@router.patch(
    "/population/{record_id}",
    response_model=FishPopulationRecordResponse,
)
async def update_population_record(
    record_id: UUID,
    payload: FishPopulationRecordUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    record = await session.get(
        FishPopulationRecord,
        record_id,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fish population record not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    # Preserve original recorder provenance.
    # The authenticated modifier is instead captured
    # by AuditLog.user_id.
    updates.pop(
        "recorded_by_user_id",
        None,
    )

    old_value = {
        field: _audit_value(
            getattr(
                record,
                field,
            )
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            record,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        record
    )

    new_value = {
        field: _audit_value(
            getattr(
                record,
                field,
            )
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="fish_population_record",
        entity_id=record.id,
        old_value=old_value,
        new_value=new_value,
    )

    return record


@router.delete(
    "/population/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_population_record(
    record_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    record = await session.get(
        FishPopulationRecord,
        record_id,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fish population record not found",
        )

    old_value = (
        _fish_population_record_audit_snapshot(
            record
        )
    )

    entity_id = record.id

    await session.delete(
        record
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="fish_population_record",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )


# ============================================================
# Feeding Events
# ============================================================

@router.get(
    "/events",
    response_model=list[FeedingEventResponse],
)
async def list_feeding_events(
    tank_id: UUID | None = None,
    schedule_id: UUID | None = None,
    status_filter: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    query = (
        select(FeedingEvent)
        .order_by(FeedingEvent.executed_at.desc())
    )

    if tank_id is not None:
        query = query.where(
            FeedingEvent.tank_id == tank_id
        )

    if schedule_id is not None:
        query = query.where(
            FeedingEvent.schedule_id == schedule_id
        )

    if status_filter is not None:
        query = query.where(
            FeedingEvent.status == status_filter
        )

    result = await session.execute(query)

    return result.scalars().all()

@router.get(
    "/events/history",
    response_model=list[FeedingEventResponse],
)
async def get_feeding_event_history(
    system_id: UUID,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> list[FeedingEvent]:
    system = await session.get(
        AquaponicsSystem,
        system_id,
    )

    if (
        system is None
        or system.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquaponics system not found",
        )

    query = (
        select(FeedingEvent)
        .join(
            Tank,
            FeedingEvent.tank_id == Tank.id,
        )
        .where(
            Tank.system_id == system_id
        )
        .order_by(
            FeedingEvent.executed_at.desc(),
            FeedingEvent.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(
        query
    )

    return list(
        result.scalars().all()
    )

@router.get(
    "/events/{event_id}",
    response_model=FeedingEventResponse,
)
async def get_feeding_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    event = await session.get(
        FeedingEvent,
        event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeding event not found",
        )

    return event


@router.post(
    "/events",
    response_model=FeedingEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feeding_event(
    payload: FeedingEventCreate,
    session: AsyncSession = Depends(get_db_session),
):
    tank = await session.get(
        Tank,
        payload.tank_id,
    )

    if tank is None or tank.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tank not found",
        )

    actuator_event = await session.get(
        ActuatorEvent,
        payload.actuator_event_id,
    )

    if actuator_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actuator event not found",
        )

    if payload.schedule_id is not None:
        schedule = await session.get(
            FeedingSchedule,
            payload.schedule_id,
        )

        if schedule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feeding schedule not found",
            )

    if payload.calibration_id is not None:
        calibration = await session.get(
            FeederCalibration,
            payload.calibration_id,
        )

        if calibration is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feeder calibration not found",
            )

    event = FeedingEvent(
        schedule_id=payload.schedule_id,
        actuator_event_id=payload.actuator_event_id,
        tank_id=payload.tank_id,
        amount_grams=payload.amount_grams,
        duration_seconds=payload.duration_seconds,
        calculated_from_biomass=payload.calculated_from_biomass,
        calibration_id=payload.calibration_id,
        executed_at=payload.executed_at,
        status=payload.status,
        notes=payload.notes,
    )

    session.add(event)

    await session.commit()
    await session.refresh(event)

    return event


@router.patch(
    "/events/{event_id}",
    response_model=FeedingEventResponse,
)
async def update_feeding_event(
    event_id: UUID,
    payload: FeedingEventUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    event = await session.get(
        FeedingEvent,
        event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeding event not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    if "tank_id" in updates:
        tank = await session.get(
            Tank,
            updates["tank_id"],
        )

        if tank is None or tank.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tank not found",
            )

    if "schedule_id" in updates and updates["schedule_id"] is not None:
        schedule = await session.get(
            FeedingSchedule,
            updates["schedule_id"],
        )

        if schedule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feeding schedule not found",
            )

    if "calibration_id" in updates and updates["calibration_id"] is not None:
        calibration = await session.get(
            FeederCalibration,
            updates["calibration_id"],
        )

        if calibration is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feeder calibration not found",
            )

    for field, value in updates.items():
        setattr(event, field, value)

    await session.commit()
    await session.refresh(event)

    return event


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_feeding_event(
    event_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    event = await session.get(
        FeedingEvent,
        event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeding event not found",
        )

    old_value = (
        _feeding_event_audit_snapshot(
            event
        )
    )

    entity_id = event.id

    await session.delete(
        event
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="feeding_event",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )