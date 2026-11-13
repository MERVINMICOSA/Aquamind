from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import (
    create_engine,
    create_session_factory,
)
from app.api.dependencies import (
    get_current_user,
    get_db_session,
)
from app.hardware.runtime import (
    build_hardware_actuator_executor,
    shutdown_hardware_actuator_executor,
)
from app.hardware.sensor_runtime import (
    build_hardware_sensor_runtime,
)
from app.services.esp32_serial_service import Esp32SerialWorker
from app.services.esp32_sensor_bridge import parse_sensor_mapping
from uuid import UUID

from app.api.esp32_telemetry import router as esp32_telemetry_router

from app.api.systems import (
    router as systems_router,
)
from app.api.tanks import (
    router as tanks_router,
)
from app.api.grow_beds import (
    router as grow_beds_router,
)
from app.api.reservoirs import (
    router as reservoirs_router,
)
from app.api.sensors import (
    router as sensors_router,
)
from app.api.sensor_readings import (
    router as sensor_readings_router,
)
from app.api.alert_thresholds import (
    router as alert_thresholds_router,
)
from app.api.alerts import (
    router as alerts_router,
)
from app.api.actuators import (
    router as actuators_router,
)
from app.api.actuator_events import (
    router as actuator_events_router,
)
from app.api.sensor_calibrations import (
    router as sensor_calibrations_router,
)
from app.api.automation_rules import (
    router as automation_rules_router,
)
from app.api.automation_runs import (
    router as automation_runs_router,
)
from app.api.feeding import (
    router as feeding_router,
)
from app.api.refill import (
    router as refill_router,
)
from app.api.system_settings import (
    router as system_settings_router,
)
from app.api.system_events import (
    router as system_events_router,
)
from app.api.auth import (
    router as auth_router,
)


# ============================================================
# DATABASE
# ============================================================


engine = create_engine(
    settings.DATABASE_URL
)

SessionFactory = (
    create_session_factory(
        engine
    )
)


# ============================================================
# APPLICATION LIFESPAN
# ============================================================


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    AquaMind application lifecycle.

    Physical hardware is initialized only when explicitly
    enabled in deployment configuration.

    Startup order:

        actuator hardware
        -> sensor runtime
        -> sensor worker

    Shutdown order:

        sensor worker
        -> actuator hardware

    This ensures physical sensor automation can never continue
    running after the actuator execution layer has been closed.
    """

    # ========================================================
    # SAFE INITIAL STATE
    # ========================================================

    app.state.actuator_executor = None
    app.state.hardware_sensor_runtime = None
    app.state.esp32_serial_worker = None

    executor = None
    sensor_runtime = None
    esp32_serial_worker = None

    try:
        # ====================================================
        # ACTUATOR HARDWARE
        # ====================================================

        executor = (
            await build_hardware_actuator_executor(
                settings
            )
        )

        app.state.actuator_executor = (
            executor
        )

        # ====================================================
        # SENSOR HARDWARE
        #
        # HARDWARE_ENABLED is the deployment-level hardware
        # safety switch.
        #
        # When false:
        #
        # - no GPIO actuator hardware is initialized;
        # - no physical sensor worker is started;
        # - development/Windows environments remain hardware
        #   neutral.
        #
        # When true:
        #
        # - compose the known hardware sensor adapters;
        # - pass the same actuator executor used by the API;
        # - start the background polling worker.
        # ====================================================

        if settings.HARDWARE_ENABLED:
            sensor_runtime = (
                build_hardware_sensor_runtime(
                    session_factory=(
                        SessionFactory
                    ),
                    actuator_executor=(
                        executor
                    ),
                )
            )

            await (
                sensor_runtime
                .worker
                .start()
            )

            app.state.hardware_sensor_runtime = (
                sensor_runtime
            )

        # ====================================================
        # USB ESP32 SENSOR TELEMETRY (read-only, no GPIO control)
        # ====================================================
        # It is independent of HARDWARE_ENABLED and does not
        # give ESP32 packets access to the actuator executor.
        if settings.ESP32_SENSOR_BRIDGE_ENABLED and not settings.ESP32_SERIAL_ENABLED:
            raise ValueError("ESP32 sensor bridge requires ESP32_SERIAL_ENABLED=true")

        if settings.ESP32_SERIAL_ENABLED:
            if not settings.ESP32_SYSTEM_ID:
                raise ValueError("ESP32_SYSTEM_ID must be set for USB ingestion")

            sensor_mapping = (
                parse_sensor_mapping(settings.ESP32_SENSOR_MAP_JSON)
                if settings.ESP32_SENSOR_BRIDGE_ENABLED
                else {}
            )
            esp32_serial_worker = Esp32SerialWorker(
                session_factory=SessionFactory,
                system_id=UUID(settings.ESP32_SYSTEM_ID),
                device_id=settings.ESP32_DEVICE_ID,
                port=settings.ESP32_SERIAL_PORT,
                baudrate=settings.ESP32_SERIAL_BAUDRATE,
                sensor_mapping=sensor_mapping,
            )
            await esp32_serial_worker.start()
            app.state.esp32_serial_worker = esp32_serial_worker

        # ====================================================
        # APPLICATION RUNNING
        # ====================================================

        yield

    finally:
        # Stop USB ingestion before stopping other hardware.
        try:
            if esp32_serial_worker is not None:
                await esp32_serial_worker.stop()
        finally:
            app.state.esp32_serial_worker = None

        # ====================================================
        # SENSOR SHUTDOWN FIRST
        #
        # A physical sensor reading can trigger actuator
        # automation. Stop acquisition before closing the
        # actuator executor.
        # ====================================================

        try:
            if sensor_runtime is not None:
                await (
                    sensor_runtime
                    .worker
                    .stop()
                )

        finally:
            app.state.hardware_sensor_runtime = (
                None
            )

            # =================================================
            # ACTUATOR SHUTDOWN SECOND
            # =================================================

            try:
                await (
                    shutdown_hardware_actuator_executor(
                        executor
                    )
                )

            finally:
                # Never expose closed hardware after shutdown.
                app.state.actuator_executor = None


# ============================================================
# FASTAPI APPLICATION
# ============================================================


app = FastAPI(
    title="AquaMind API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
    ],
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Accept",
        "Authorization",
        "Content-Type",
    ],
)

# ============================================================
# APPLICATION STATE
# ============================================================


app.state.session_factory = (
    SessionFactory
)

# Hardware-neutral actuator execution boundary.
#
# Physical actuator hardware remains unavailable until
# deployment explicitly enables it.
app.state.actuator_executor = None

# Hardware-neutral physical sensor runtime boundary.
#
# The background sensor worker is created only while hardware
# is explicitly enabled.
app.state.hardware_sensor_runtime = None
app.state.esp32_serial_worker = None


# ============================================================
# ROUTERS
# ============================================================


app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    systems_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    system_settings_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    tanks_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    grow_beds_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    reservoirs_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    sensors_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    sensor_readings_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    alert_thresholds_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    alerts_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    actuators_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    actuator_events_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    automation_rules_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    automation_runs_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    sensor_calibrations_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    feeding_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    refill_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)

app.include_router(
    system_events_router,
    prefix="/api/v1",
    dependencies=[
        Depends(
            get_current_user
        )
    ],
)


# USB serial ingestion is local; telemetry GET endpoints require login.
app.include_router(esp32_telemetry_router, prefix="/api/v1")


# ============================================================
# HEALTH
# ============================================================


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


@app.get("/db-health")
async def db_health():
    try:
        async with engine.connect() as connection:
            result = (
                await connection.execute(
                    text(
                        "SELECT "
                        "current_database(), "
                        "current_user"
                    )
                )
            )

            database, user = (
                result.one()
            )

        return {
            "status": "ok",
            "database": database,
            "user": user,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": (
                    "Database connection failed"
                ),
            },
        ) from exc


@app.get("/db-session-health")
async def db_session_health(
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    result = await session.execute(
        text(
            "SELECT 1"
        )
    )

    return {
        "status": "ok",
        "session": "ok",
    }