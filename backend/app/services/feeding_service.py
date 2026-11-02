from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ActuatorType, LocationType
from app.models.actuators import Actuator
from app.models.feeding import (
    FeederCalibration,
    FeedingSchedule,
    FishPopulationRecord,
)
from app.models.system import Tank


# ============================================================
# EXCEPTIONS
# ============================================================


class FeedingCalculationError(ValueError):
    """Raised when a feeding calculation cannot be performed safely."""


class FeedingContextError(ValueError):
    """Raised when required feeding context is missing or inconsistent."""


# ============================================================
# DATA OBJECTS
# ============================================================


@dataclass(frozen=True, slots=True)
class FeedingPlan:
    biomass_grams: float
    daily_feed_rate_percent: float
    feeds_per_day: int

    daily_feed_grams: float
    uncapped_amount_grams: float
    amount_grams: float

    max_per_feed_grams: float
    capped_by_schedule: bool

    grams_per_second: float
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class FeedingContext:
    schedule: FeedingSchedule
    actuator: Actuator
    tank: Tank
    population: FishPopulationRecord
    calibration: FeederCalibration
    max_runtime_seconds: float | None


@dataclass(frozen=True, slots=True)
class PreparedFeedingPlan:
    schedule_id: UUID
    actuator_id: UUID
    tank_id: UUID

    population_record_id: UUID
    calibration_id: UUID

    max_runtime_seconds: float
    plan: FeedingPlan


# ============================================================
# CALCULATION KERNEL
# ============================================================


def calculate_grams_per_second(
    *,
    measured_grams: float,
    measured_seconds: float,
) -> float:
    if measured_grams <= 0:
        raise FeedingCalculationError(
            "Measured grams must be greater than zero"
        )

    if measured_seconds <= 0:
        raise FeedingCalculationError(
            "Measured seconds must be greater than zero"
        )

    return measured_grams / measured_seconds


def calculate_feed_amount_per_feeding(
    *,
    biomass_grams: float,
    daily_feed_rate_percent: float,
    feeds_per_day: int,
    max_per_feed_grams: float,
) -> float:
    if biomass_grams < 0:
        raise FeedingCalculationError(
            "Biomass cannot be negative"
        )

    if daily_feed_rate_percent <= 0:
        raise FeedingCalculationError(
            "Daily feed rate percent must be greater than zero"
        )

    if feeds_per_day <= 0:
        raise FeedingCalculationError(
            "Feeds per day must be greater than zero"
        )

    if max_per_feed_grams <= 0:
        raise FeedingCalculationError(
            "Maximum feed amount must be greater than zero"
        )

    if biomass_grams == 0:
        return 0.0

    daily_feed_grams = (
        biomass_grams
        * daily_feed_rate_percent
        / 100.0
    )

    amount_per_feed = (
        daily_feed_grams
        / feeds_per_day
    )

    return min(
        amount_per_feed,
        max_per_feed_grams,
    )


def calculate_feed_duration_seconds(
    *,
    amount_grams: float,
    grams_per_second: float,
) -> float:
    if amount_grams < 0:
        raise FeedingCalculationError(
            "Feed amount cannot be negative"
        )

    if grams_per_second <= 0:
        raise FeedingCalculationError(
            "Feeder calibration rate must be greater than zero"
        )

    if amount_grams == 0:
        return 0.0

    return amount_grams / grams_per_second


def build_feeding_plan(
    *,
    biomass_grams: float,
    daily_feed_rate_percent: float,
    feeds_per_day: int,
    max_per_feed_grams: float,
    measured_grams: float,
    measured_seconds: float,
    max_runtime_seconds: float | None = None,
) -> FeedingPlan:
    grams_per_second = calculate_grams_per_second(
        measured_grams=measured_grams,
        measured_seconds=measured_seconds,
    )

    amount_grams = calculate_feed_amount_per_feeding(
        biomass_grams=biomass_grams,
        daily_feed_rate_percent=daily_feed_rate_percent,
        feeds_per_day=feeds_per_day,
        max_per_feed_grams=max_per_feed_grams,
    )

    daily_feed_grams = (
        biomass_grams
        * daily_feed_rate_percent
        / 100.0
    )

    uncapped_amount_grams = (
        daily_feed_grams
        / feeds_per_day
    )

    duration_seconds = calculate_feed_duration_seconds(
        amount_grams=amount_grams,
        grams_per_second=grams_per_second,
    )

    if max_runtime_seconds is not None:
        if max_runtime_seconds <= 0:
            raise FeedingCalculationError(
                "Maximum runtime must be greater than zero"
            )

        if duration_seconds > max_runtime_seconds:
            raise FeedingCalculationError(
                "Calculated feeder runtime exceeds actuator safety limit"
            )

    return FeedingPlan(
        biomass_grams=biomass_grams,
        daily_feed_rate_percent=daily_feed_rate_percent,
        feeds_per_day=feeds_per_day,
        daily_feed_grams=daily_feed_grams,
        uncapped_amount_grams=uncapped_amount_grams,
        amount_grams=amount_grams,
        max_per_feed_grams=max_per_feed_grams,
        capped_by_schedule=(
            amount_grams < uncapped_amount_grams
        ),
        grams_per_second=grams_per_second,
        duration_seconds=duration_seconds,
    )


# ============================================================
# ACTUATOR SAFETY
# ============================================================


def _extract_max_runtime_seconds(
    actuator: Actuator,
) -> float | None:
    safety_config = actuator.safety_config or {}

    raw_value = safety_config.get(
        "max_runtime_seconds"
    )

    if raw_value is None:
        return None

    try:
        max_runtime_seconds = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise FeedingContextError(
            "Actuator max runtime safety limit is invalid"
        ) from exc

    if max_runtime_seconds <= 0:
        raise FeedingContextError(
            "Actuator max runtime safety limit must be greater than zero"
        )

    return max_runtime_seconds


# ============================================================
# FEEDING CONTEXT RESOLUTION
# ============================================================


async def resolve_feeding_context(
    session: AsyncSession,
    *,
    schedule_id: UUID,
    tank_id: UUID,
    as_of: datetime | None = None,
) -> FeedingContext:
    effective_time = as_of or datetime.now(
        timezone.utc
    )

    if effective_time.tzinfo is None:
        raise FeedingContextError(
            "Feeding context time must be timezone-aware"
        )

    # --------------------------------------------------------
    # Feeding schedule
    # --------------------------------------------------------

    schedule = await session.get(
        FeedingSchedule,
        schedule_id,
    )

    if schedule is None:
        raise FeedingContextError(
            "Feeding schedule not found"
        )

    if not schedule.enabled:
        raise FeedingContextError(
            "Feeding schedule is disabled"
        )

    # --------------------------------------------------------
    # Target tank
    # --------------------------------------------------------

    tank = await session.get(
        Tank,
        tank_id,
    )

    if tank is None or tank.deleted_at is not None:
        raise FeedingContextError(
            "Tank not found"
        )

    if not tank.is_active:
        raise FeedingContextError(
            "Tank is inactive"
        )

    if tank.system_id != schedule.system_id:
        raise FeedingContextError(
            "Target tank does not belong to the feeding schedule system"
        )

    # --------------------------------------------------------
    # Feeder actuator
    # --------------------------------------------------------

    actuator = await session.get(
        Actuator,
        schedule.actuator_id,
    )

    if actuator is None or actuator.deleted_at is not None:
        raise FeedingContextError(
            "Feeder actuator not found"
        )

    if not actuator.is_enabled:
        raise FeedingContextError(
            "Feeder actuator is disabled"
        )

    if actuator.actuator_type != ActuatorType.FISH_FEEDER:
        raise FeedingContextError(
            "Feeding schedule actuator is not a fish feeder"
        )

    if actuator.system_id != schedule.system_id:
        raise FeedingContextError(
            "Feeder actuator does not belong to the feeding schedule system"
        )

    if actuator.location_type != LocationType.TANK:
        raise FeedingContextError(
            "Fish feeder must be assigned to a tank"
        )

    if actuator.location_id != tank.id:
        raise FeedingContextError(
            "Fish feeder is not assigned to the target tank"
        )

    # --------------------------------------------------------
    # Latest applicable fish population
    # --------------------------------------------------------

    population_result = await session.execute(
        select(FishPopulationRecord)
        .where(
            FishPopulationRecord.tank_id == tank.id,
            FishPopulationRecord.effective_at <= effective_time,
        )
        .order_by(
            FishPopulationRecord.effective_at.desc()
        )
        .limit(1)
    )

    population = (
        population_result.scalars().first()
    )

    if population is None:
        raise FeedingContextError(
            "No applicable fish population record found"
        )

    if population.estimated_biomass_grams is None:
        raise FeedingContextError(
            "Latest fish population record does not contain a biomass estimate"
        )

    # --------------------------------------------------------
    # Latest applicable feeder calibration
    # --------------------------------------------------------

    calibration_result = await session.execute(
        select(FeederCalibration)
        .where(
            FeederCalibration.actuator_id == actuator.id,
            FeederCalibration.performed_at <= effective_time,
        )
        .order_by(
            FeederCalibration.performed_at.desc()
        )
        .limit(1)
    )

    calibration = (
        calibration_result.scalars().first()
    )

    if calibration is None:
        raise FeedingContextError(
            "No applicable feeder calibration found"
        )

    # --------------------------------------------------------
    # Actuator safety configuration
    # --------------------------------------------------------

    max_runtime_seconds = (
        _extract_max_runtime_seconds(
            actuator
        )
    )

    # --------------------------------------------------------
    # Complete context
    # --------------------------------------------------------

    return FeedingContext(
        schedule=schedule,
        actuator=actuator,
        tank=tank,
        population=population,
        calibration=calibration,
        max_runtime_seconds=max_runtime_seconds,
    )


# ============================================================
# PREPARED FEEDING PLAN
# ============================================================


async def prepare_feeding_plan(
    session: AsyncSession,
    *,
    schedule_id: UUID,
    tank_id: UUID,
    daily_feed_rate_percent: float,
    feeds_per_day: int,
    as_of: datetime | None = None,
) -> PreparedFeedingPlan:
    context = await resolve_feeding_context(
        session,
        schedule_id=schedule_id,
        tank_id=tank_id,
        as_of=as_of,
    )

    # Automated feeding requires an explicit safety limit.
    if context.max_runtime_seconds is None:
        raise FeedingContextError(
            "Fish feeder requires a maximum runtime safety limit"
        )

    biomass_grams = float(
        context.population.estimated_biomass_grams
    )

    plan = build_feeding_plan(
        biomass_grams=biomass_grams,
        daily_feed_rate_percent=daily_feed_rate_percent,
        feeds_per_day=feeds_per_day,
        max_per_feed_grams=float(
            context.schedule.max_per_feed_grams
        ),
        measured_grams=float(
            context.calibration.measured_grams
        ),
        measured_seconds=float(
            context.calibration.measured_seconds
        ),
        max_runtime_seconds=(
            context.max_runtime_seconds
        ),
    )

    return PreparedFeedingPlan(
        schedule_id=context.schedule.id,
        actuator_id=context.actuator.id,
        tank_id=context.tank.id,
        population_record_id=context.population.id,
        calibration_id=context.calibration.id,
        max_runtime_seconds=(
            context.max_runtime_seconds
        ),
        plan=plan,
    )