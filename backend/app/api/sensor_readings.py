from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_actuator_executor,
    get_db_session,
)
from app.models.sensors import Sensor, SensorReading
from app.schemas.sensor_reading import (
    SensorReadingCreate,
    SensorReadingResponse,
)
from app.services.actuator_executor import (
    ActuatorExecutor,
)
from app.services.alert_service import (
    process_sensor_reading,
)
from app.services.sensor_automation_service import (
    process_sensor_reading_automation,
)


router = APIRouter(
    prefix="/sensor-readings",
    tags=["sensor-readings"],
)


# ============================================================
# LIST SENSOR READINGS
# ============================================================

@router.get(
    "",
    response_model=list[SensorReadingResponse],
)
async def list_sensor_readings(
    sensor_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    List sensor readings.

    If sensor_id is provided, only readings belonging to that
    sensor are returned.

    Readings are ordered newest first.
    """

    query = (
        select(SensorReading)
        .order_by(SensorReading.recorded_at.desc())
    )

    if sensor_id is not None:
        query = query.where(
            SensorReading.sensor_id == sensor_id
        )

    result = await session.execute(query)

    return result.scalars().all()

# ============================================================
# LIST LATEST SENSOR READINGS
# ============================================================


@router.get(
    "/latest",
    response_model=list[SensorReadingResponse],
)
async def list_latest_sensor_readings(
    system_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    """
    Return at most one newest reading for every
    non-deleted sensor belonging to the requested system.

    Selection order per sensor:

    1. recorded_at DESC
    2. created_at DESC
    3. id DESC

    Sensors without readings are not included.
    """

    ranked_readings = (
        select(
            SensorReading.id.label(
                "reading_id"
            ),
            func.row_number()
            .over(
                partition_by=(
                    SensorReading.sensor_id
                ),
                order_by=(
                    SensorReading.recorded_at.desc(),
                    SensorReading.created_at.desc(),
                    SensorReading.id.desc(),
                ),
            )
            .label("reading_rank"),
        )
        .join(
            Sensor,
            Sensor.id
            == SensorReading.sensor_id,
        )
        .where(
            Sensor.system_id
            == system_id,
            Sensor.deleted_at.is_(None),
        )
        .subquery()
    )

    query = (
        select(
            SensorReading
        )
        .join(
            ranked_readings,
            SensorReading.id
            == ranked_readings.c.reading_id,
        )
        .where(
            ranked_readings.c.reading_rank
            == 1
        )
        .order_by(
            SensorReading.recorded_at.desc(),
            SensorReading.created_at.desc(),
            SensorReading.id.desc(),
        )
    )

    result = await session.execute(
        query
    )

    return result.scalars().all()

# ============================================================
# LIST SENSOR READING HISTORY
# ============================================================


@router.get(
    "/history",
    response_model=list[SensorReadingResponse],
)
async def list_sensor_reading_history(
    sensor_id: UUID,
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
):
    """
    Return a bounded page of persisted readings for one sensor.

    Readings are ordered deterministically newest first.

    The caller controls pagination with:

    - limit: 1 through 100, default 50
    - offset: zero-based row offset

    This endpoint intentionally avoids returning an
    unbounded sensor history to monitoring clients.
    """

    sensor = await session.get(
        Sensor,
        sensor_id,
    )

    if (
        sensor is None
        or sensor.deleted_at is not None
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Sensor not found",
        )

    query = (
        select(
            SensorReading
        )
        .where(
            SensorReading.sensor_id
            == sensor_id
        )
        .order_by(
            SensorReading.recorded_at.desc(),
            SensorReading.created_at.desc(),
            SensorReading.id.desc(),
        )
        .offset(
            offset
        )
        .limit(
            limit
        )
    )

    result = await session.execute(
        query
    )

    return result.scalars().all()

# ============================================================
# GET SENSOR READING
# ============================================================

@router.get(
    "/{reading_id}",
    response_model=SensorReadingResponse,
)
async def get_sensor_reading(
    reading_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve a single sensor reading by ID.
    """

    reading = await session.get(
        SensorReading,
        reading_id,
    )

    if reading is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor reading not found",
        )

    return reading


# ============================================================
# CREATE SENSOR READING
# ============================================================


@router.post(
    "",
    response_model=SensorReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sensor_reading(
    payload: SensorReadingCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    actuator_executor: ActuatorExecutor | None = Depends(
        get_actuator_executor
    ),
):
    """
    Create and persist a sensor reading.

    Runtime order:

    1. Validate the owning sensor.
    2. Persist the reading.
    3. Process alert rules.
    4. If a real actuator executor is configured, process
       sensor-triggered automation.

    Sensor telemetry is persisted before any downstream
    automation processing begins.
    """

    # --------------------------------------------------------
    # SENSOR
    # --------------------------------------------------------

    sensor = await session.get(
        Sensor,
        payload.sensor_id,
    )

    # --------------------------------------------------------
    # SENSOR MUST EXIST AND MUST NOT BE SOFT-DELETED
    # --------------------------------------------------------

    if (
        sensor is None
        or sensor.deleted_at is not None
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Sensor not found",
        )

    # --------------------------------------------------------
    # DISABLED SENSOR
    # --------------------------------------------------------

    if not sensor.is_enabled:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail="Sensor is disabled",
        )

    # --------------------------------------------------------
    # CREATE READING
    # --------------------------------------------------------

    reading = SensorReading(
        sensor_id=payload.sensor_id,
        recorded_at=payload.recorded_at,
        value_numeric=payload.value_numeric,
        unit=payload.unit,
        quality_status=(
            payload.quality_status
        ),
        source=payload.source,
        sequence_number=(
            payload.sequence_number
        ),
    )

    session.add(
        reading
    )

    # --------------------------------------------------------
    # TELEMETRY COMMIT BOUNDARY
    #
    # The sensor reading becomes durable before alerts or
    # automation are processed.
    # --------------------------------------------------------

    await session.commit()

    await session.refresh(
        reading
    )

    # --------------------------------------------------------
    # ALERT PROCESSING
    #
    # Existing Phase 6 alert behavior remains unchanged.
    # --------------------------------------------------------

    await process_sensor_reading(
        session,
        reading,
    )

    # --------------------------------------------------------
    # AUTOMATION PROCESSING
    #
    # Never fabricate hardware success.
    #
    # Without a configured executor, telemetry and alerts
    # continue normally while actuator execution is skipped.
    #
    # Phase 9 will install the real ActuatorExecutor.
    # --------------------------------------------------------

    if actuator_executor is not None:
        await process_sensor_reading_automation(
            session,
            reading=reading,
            executor=actuator_executor,
        )

    return reading