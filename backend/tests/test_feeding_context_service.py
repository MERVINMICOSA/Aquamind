from datetime import datetime, timedelta, timezone

import pytest

from app.db.enums import (
    ActuatorType,
    ControlMode,
    LocationType,
)
from app.models.actuators import Actuator
from app.models.feeding import (
    FeederCalibration,
    FeedingSchedule,
    FishPopulationRecord,
)
from app.models.system import (
    AquaponicsSystem,
    Tank,
)
from app.services.feeding_service import (
    FeedingCalculationError,
    FeedingContextError,
    prepare_feeding_plan,
    resolve_feeding_context,
)


pytestmark = pytest.mark.asyncio


# ============================================================
# HELPERS
# ============================================================


async def create_system(
    session,
    *,
    name="Feeding Context Test System",
):
    system = AquaponicsSystem(
        name=name,
    )

    session.add(system)
    await session.commit()
    await session.refresh(system)

    return system


async def create_tank(
    session,
    system,
    *,
    name="Feeding Context Tank",
    is_active=True,
):
    tank = Tank(
        system_id=system.id,
        name=name,
        capacity_liters=1000.0,
        species="Tilapia",
        is_active=is_active,
    )

    session.add(tank)
    await session.commit()
    await session.refresh(tank)

    return tank


async def create_feeder(
    session,
    system,
    tank,
    *,
    actuator_type=ActuatorType.FISH_FEEDER,
    is_enabled=True,
    location_type=LocationType.TANK,
    location_id=None,
    safety_config=None,
):
    actuator = Actuator(
        system_id=system.id,
        name="Context Test Feeder",
        actuator_type=actuator_type,
        control_mode=ControlMode.SCHEDULED,
        hardware_identifier=None,
        location_type=location_type,
        location_id=(
            tank.id
            if location_id is None
            else location_id
        ),
        is_enabled=is_enabled,
        safety_config=(
            {
                "max_runtime_seconds": 30.0,
            }
            if safety_config is None
            else safety_config
        ),
    )

    session.add(actuator)
    await session.commit()
    await session.refresh(actuator)

    return actuator


async def create_schedule(
    session,
    system,
    actuator,
    *,
    enabled=True,
):
    schedule = FeedingSchedule(
        system_id=system.id,
        actuator_id=actuator.id,
        name="Context Feeding Schedule",
        schedule_expression="0 8 * * *",
        enabled=enabled,
        max_per_feed_grams=100.0,
    )

    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)

    return schedule


async def create_population(
    session,
    tank,
    *,
    biomass=25000.0,
    effective_at=None,
):
    record = FishPopulationRecord(
        tank_id=tank.id,
        species="Tilapia",
        count=100,
        estimated_biomass_grams=biomass,
        effective_at=(
            effective_at
            or datetime.now(timezone.utc)
        ),
        recorded_by_user_id=None,
        notes=None,
    )

    session.add(record)
    await session.commit()
    await session.refresh(record)

    return record


async def create_calibration(
    session,
    actuator,
    *,
    performed_at=None,
    measured_grams=50.0,
    measured_seconds=10.0,
):
    calibration = FeederCalibration(
        actuator_id=actuator.id,
        run_count=5,
        measured_seconds=measured_seconds,
        measured_grams=measured_grams,
        grams_per_second=(
            measured_grams
            / measured_seconds
        ),
        calibration_method="measured_average",
        performed_at=(
            performed_at
            or datetime.now(timezone.utc)
        ),
        verified_by_user_id=None,
        notes=None,
    )

    session.add(calibration)
    await session.commit()
    await session.refresh(calibration)

    return calibration


# ============================================================
# LATEST APPLICABLE CONTEXT
# ============================================================


async def test_resolve_feeding_context_uses_latest_applicable_records(
    test_session,
):
    base_time = datetime.now(timezone.utc)

    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    older_population = await create_population(
        test_session,
        tank,
        biomass=20000.0,
        effective_at=(
            base_time
            - timedelta(days=2)
        ),
    )

    newer_population = await create_population(
        test_session,
        tank,
        biomass=25000.0,
        effective_at=(
            base_time
            - timedelta(days=1)
        ),
    )

    await create_population(
        test_session,
        tank,
        biomass=30000.0,
        effective_at=(
            base_time
            + timedelta(days=1)
        ),
    )

    older_calibration = await create_calibration(
        test_session,
        actuator,
        performed_at=(
            base_time
            - timedelta(days=2)
        ),
        measured_grams=40.0,
        measured_seconds=10.0,
    )

    newer_calibration = await create_calibration(
        test_session,
        actuator,
        performed_at=(
            base_time
            - timedelta(hours=12)
        ),
        measured_grams=50.0,
        measured_seconds=10.0,
    )

    await create_calibration(
        test_session,
        actuator,
        performed_at=(
            base_time
            + timedelta(hours=1)
        ),
        measured_grams=60.0,
        measured_seconds=10.0,
    )

    context = await resolve_feeding_context(
        test_session,
        schedule_id=schedule.id,
        tank_id=tank.id,
        as_of=base_time,
    )

    assert (
        older_population.id
        != newer_population.id
    )

    assert (
        older_calibration.id
        != newer_calibration.id
    )

    assert (
        context.population.id
        == newer_population.id
    )

    assert (
        context.calibration.id
        == newer_calibration.id
    )

    assert (
        float(
            context.population
            .estimated_biomass_grams
        )
        == 25000.0
    )

    assert context.max_runtime_seconds == 30.0


# ============================================================
# DISABLED SCHEDULE
# ============================================================


async def test_disabled_schedule_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
        enabled=False,
    )

    with pytest.raises(
        FeedingContextError,
        match="Feeding schedule is disabled",
    ):
        await resolve_feeding_context(
            test_session,
            schedule_id=schedule.id,
            tank_id=tank.id,
        )


# ============================================================
# WRONG ACTUATOR TYPE
# ============================================================


async def test_non_feeder_actuator_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
        actuator_type=ActuatorType.WATER_PUMP,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    with pytest.raises(
        FeedingContextError,
        match=(
            "Feeding schedule actuator "
            "is not a fish feeder"
        ),
    ):
        await resolve_feeding_context(
            test_session,
            schedule_id=schedule.id,
            tank_id=tank.id,
        )


# ============================================================
# DISABLED ACTUATOR
# ============================================================


async def test_disabled_feeder_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
        is_enabled=False,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    with pytest.raises(
        FeedingContextError,
        match="Feeder actuator is disabled",
    ):
        await resolve_feeding_context(
            test_session,
            schedule_id=schedule.id,
            tank_id=tank.id,
        )


# ============================================================
# CROSS-SYSTEM TANK
# ============================================================


async def test_tank_must_belong_to_schedule_system(
    test_session,
):
    first_system = await create_system(
        test_session,
        name="Schedule System",
    )

    second_system = await create_system(
        test_session,
        name="Other Tank System",
    )

    feeder_tank = await create_tank(
        test_session,
        first_system,
        name="Feeder Tank",
    )

    target_tank = await create_tank(
        test_session,
        second_system,
        name="Other Tank",
    )

    actuator = await create_feeder(
        test_session,
        first_system,
        feeder_tank,
    )

    schedule = await create_schedule(
        test_session,
        first_system,
        actuator,
    )

    with pytest.raises(
        FeedingContextError,
        match=(
            "Target tank does not belong "
            "to the feeding schedule system"
        ),
    ):
        await resolve_feeding_context(
            test_session,
            schedule_id=schedule.id,
            tank_id=target_tank.id,
        )


# ============================================================
# WRONG TANK LOCATION
# ============================================================


async def test_feeder_must_be_assigned_to_target_tank(
    test_session,
):
    system = await create_system(
        test_session
    )

    feeder_tank = await create_tank(
        test_session,
        system,
        name="Feeder Tank",
    )

    target_tank = await create_tank(
        test_session,
        system,
        name="Target Tank",
    )

    actuator = await create_feeder(
        test_session,
        system,
        feeder_tank,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    with pytest.raises(
        FeedingContextError,
        match=(
            "Fish feeder is not assigned "
            "to the target tank"
        ),
    ):
        await resolve_feeding_context(
            test_session,
            schedule_id=schedule.id,
            tank_id=target_tank.id,
        )


# ============================================================
# POPULATION REQUIRED
# ============================================================


async def test_population_record_is_required(
    test_session,
):
    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    await create_calibration(
        test_session,
        actuator,
    )

    with pytest.raises(
        FeedingContextError,
        match=(
            "No applicable fish population "
            "record found"
        ),
    ):
        await resolve_feeding_context(
            test_session,
            schedule_id=schedule.id,
            tank_id=tank.id,
        )


# ============================================================
# BIOMASS REQUIRED
# ============================================================


async def test_population_requires_biomass_estimate(
    test_session,
):
    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    await create_population(
        test_session,
        tank,
        biomass=None,
    )

    await create_calibration(
        test_session,
        actuator,
    )

    with pytest.raises(
        FeedingContextError,
        match=(
            "Latest fish population record "
            "does not contain a biomass estimate"
        ),
    ):
        await resolve_feeding_context(
            test_session,
            schedule_id=schedule.id,
            tank_id=tank.id,
        )


# ============================================================
# CALIBRATION REQUIRED
# ============================================================


async def test_feeder_calibration_is_required(
    test_session,
):
    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    await create_population(
        test_session,
        tank,
    )

    with pytest.raises(
        FeedingContextError,
        match=(
            "No applicable feeder "
            "calibration found"
        ),
    ):
        await resolve_feeding_context(
            test_session,
            schedule_id=schedule.id,
            tank_id=tank.id,
        )


# ============================================================
# PREPARED FEEDING PLAN
# ============================================================


async def test_prepare_feeding_plan_builds_complete_plan(
    test_session,
):
    base_time = datetime.now(timezone.utc)

    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    population = await create_population(
        test_session,
        tank,
        biomass=25000.0,
        effective_at=(
            base_time
            - timedelta(minutes=2)
        ),
    )

    calibration = await create_calibration(
        test_session,
        actuator,
        performed_at=(
            base_time
            - timedelta(minutes=1)
        ),
        measured_grams=50.0,
        measured_seconds=10.0,
    )

    prepared = await prepare_feeding_plan(
        test_session,
        schedule_id=schedule.id,
        tank_id=tank.id,
        daily_feed_rate_percent=1.0,
        feeds_per_day=5,
        as_of=base_time,
    )

    assert prepared.schedule_id == schedule.id
    assert prepared.actuator_id == actuator.id
    assert prepared.tank_id == tank.id

    assert (
        prepared.population_record_id
        == population.id
    )

    assert (
        prepared.calibration_id
        == calibration.id
    )

    assert prepared.max_runtime_seconds == 30.0

    assert prepared.plan.biomass_grams == pytest.approx(
        25000.0
    )

    assert prepared.plan.daily_feed_grams == pytest.approx(
        250.0
    )

    assert prepared.plan.amount_grams == pytest.approx(
        50.0
    )

    assert prepared.plan.grams_per_second == pytest.approx(
        5.0
    )

    assert prepared.plan.duration_seconds == pytest.approx(
        10.0
    )

    assert prepared.plan.capped_by_schedule is False


# ============================================================
# SCHEDULE CAP INTEGRATION
# ============================================================


async def test_prepare_feeding_plan_enforces_schedule_cap(
    test_session,
):
    base_time = datetime.now(timezone.utc)

    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    await create_population(
        test_session,
        tank,
        biomass=25000.0,
        effective_at=(
            base_time
            - timedelta(minutes=2)
        ),
    )

    await create_calibration(
        test_session,
        actuator,
        performed_at=(
            base_time
            - timedelta(minutes=1)
        ),
        measured_grams=50.0,
        measured_seconds=10.0,
    )

    prepared = await prepare_feeding_plan(
        test_session,
        schedule_id=schedule.id,
        tank_id=tank.id,
        daily_feed_rate_percent=2.0,
        feeds_per_day=4,
        as_of=base_time,
    )

    # 25,000 × 2% = 500 g/day
    assert prepared.plan.daily_feed_grams == pytest.approx(
        500.0
    )

    # 500 / 4 = 125 g before schedule cap
    assert prepared.plan.uncapped_amount_grams == pytest.approx(
        125.0
    )

    # schedule maximum = 100 g
    assert prepared.plan.amount_grams == pytest.approx(
        100.0
    )

    assert prepared.plan.capped_by_schedule is True

    # 100 g / 5 g/s
    assert prepared.plan.duration_seconds == pytest.approx(
        20.0
    )


# ============================================================
# ACTUATOR RUNTIME SAFETY
# ============================================================


async def test_prepare_feeding_plan_enforces_runtime_safety_limit(
    test_session,
):
    base_time = datetime.now(timezone.utc)

    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    await create_population(
        test_session,
        tank,
        biomass=25000.0,
        effective_at=(
            base_time
            - timedelta(minutes=2)
        ),
    )

    # 20 g / 10 s = 2 g/s
    await create_calibration(
        test_session,
        actuator,
        performed_at=(
            base_time
            - timedelta(minutes=1)
        ),
        measured_grams=20.0,
        measured_seconds=10.0,
    )

    with pytest.raises(
        FeedingCalculationError,
        match=(
            "Calculated feeder runtime exceeds "
            "actuator safety limit"
        ),
    ):
        await prepare_feeding_plan(
            test_session,
            schedule_id=schedule.id,
            tank_id=tank.id,
            daily_feed_rate_percent=2.0,
            feeds_per_day=4,
            as_of=base_time,
        )


# ============================================================
# RUNTIME SAFETY CONFIG REQUIRED
# ============================================================


async def test_prepare_feeding_plan_requires_runtime_safety_limit(
    test_session,
):
    base_time = datetime.now(timezone.utc)

    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    actuator = await create_feeder(
        test_session,
        system,
        tank,
        safety_config={},
    )

    schedule = await create_schedule(
        test_session,
        system,
        actuator,
    )

    await create_population(
        test_session,
        tank,
        biomass=25000.0,
        effective_at=(
            base_time
            - timedelta(minutes=2)
        ),
    )

    await create_calibration(
        test_session,
        actuator,
        performed_at=(
            base_time
            - timedelta(minutes=1)
        ),
    )

    with pytest.raises(
        FeedingContextError,
        match=(
            "Fish feeder requires a maximum "
            "runtime safety limit"
        ),
    ):
        await prepare_feeding_plan(
            test_session,
            schedule_id=schedule.id,
            tank_id=tank.id,
            daily_feed_rate_percent=1.0,
            feeds_per_day=5,
            as_of=base_time,
        )