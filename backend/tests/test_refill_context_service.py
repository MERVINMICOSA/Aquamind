from uuid import UUID

import pytest

from datetime import datetime, timedelta, timezone

from app.db.enums import ExecutionStatus, RefillTrigger


from app.models.system import (
    AquaponicsSystem,
    Reservoir,
    Tank,
)
from app.services.refill_service import (
    RefillCalculationError,
    prepare_refill_plan,
    resolve_refill_context,
)

pytestmark = pytest.mark.asyncio


# ============================================================
# HELPERS
# ============================================================


async def create_system(
    session,
    *,
    name="Refill Context System",
):
    system = AquaponicsSystem(
        name=name,
    )

    session.add(system)
    await session.commit()
    await session.refresh(system)

    return system


async def create_reservoir(
    session,
    system,
    *,
    name="Refill Reservoir",
    is_active=True,
):
    reservoir = Reservoir(
        system_id=system.id,
        name=name,
        capacity_liters=500.0,
        is_active=is_active,
    )

    session.add(reservoir)
    await session.commit()
    await session.refresh(reservoir)

    return reservoir


async def create_tank(
    session,
    system,
    *,
    name="Refill Target Tank",
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


# ============================================================
# VALID CONTEXT
# ============================================================


async def test_resolve_refill_context(
    test_session,
):
    system = await create_system(
        test_session
    )

    reservoir = await create_reservoir(
        test_session,
        system,
    )

    tank = await create_tank(
        test_session,
        system,
    )

    context = await resolve_refill_context(
        test_session,
        reservoir_id=reservoir.id,
        target_tank_id=tank.id,
    )

    assert context.reservoir.id == reservoir.id

    assert (
        context.target_tank.id
        == tank.id
    )

    assert context.system_id == system.id


# ============================================================
# RESERVOIR VALIDATION
# ============================================================


async def test_missing_reservoir_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    tank = await create_tank(
        test_session,
        system,
    )

    missing_id = UUID(
        "00000000-0000-0000-0000-000000000000"
    )

    with pytest.raises(
        RefillCalculationError,
        match="Reservoir not found",
    ):
        await resolve_refill_context(
            test_session,
            reservoir_id=missing_id,
            target_tank_id=tank.id,
        )


async def test_inactive_reservoir_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    reservoir = await create_reservoir(
        test_session,
        system,
        is_active=False,
    )

    tank = await create_tank(
        test_session,
        system,
    )

    with pytest.raises(
        RefillCalculationError,
        match="Reservoir is inactive",
    ):
        await resolve_refill_context(
            test_session,
            reservoir_id=reservoir.id,
            target_tank_id=tank.id,
        )


# ============================================================
# TARGET TANK VALIDATION
# ============================================================


async def test_missing_target_tank_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    reservoir = await create_reservoir(
        test_session,
        system,
    )

    missing_id = UUID(
        "00000000-0000-0000-0000-000000000000"
    )

    with pytest.raises(
        RefillCalculationError,
        match="Target tank not found",
    ):
        await resolve_refill_context(
            test_session,
            reservoir_id=reservoir.id,
            target_tank_id=missing_id,
        )


async def test_inactive_target_tank_is_rejected(
    test_session,
):
    system = await create_system(
        test_session
    )

    reservoir = await create_reservoir(
        test_session,
        system,
    )

    tank = await create_tank(
        test_session,
        system,
        is_active=False,
    )

    with pytest.raises(
        RefillCalculationError,
        match="Target tank is inactive",
    ):
        await resolve_refill_context(
            test_session,
            reservoir_id=reservoir.id,
            target_tank_id=tank.id,
        )


# ============================================================
# CROSS-SYSTEM SAFETY
# ============================================================


async def test_cross_system_refill_is_rejected(
    test_session,
):
    reservoir_system = await create_system(
        test_session,
        name="Reservoir System",
    )

    tank_system = await create_system(
        test_session,
        name="Tank System",
    )

    reservoir = await create_reservoir(
        test_session,
        reservoir_system,
    )

    tank = await create_tank(
        test_session,
        tank_system,
    )

    with pytest.raises(
        RefillCalculationError,
        match=(
            "Reservoir and target tank must "
            "belong to the same system"
        ),
    ):
        await resolve_refill_context(
            test_session,
            reservoir_id=reservoir.id,
            target_tank_id=tank.id,
        )


# ============================================================
# PREPARED REFILL PLAN
# ============================================================


async def test_prepare_refill_plan_combines_context_and_event_plan(
    test_session,
):
    system = await create_system(
        test_session
    )

    reservoir = await create_reservoir(
        test_session,
        system,
    )

    tank = await create_tank(
        test_session,
        system,
    )

    started_at = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    completed_at = (
        started_at
        + timedelta(seconds=60)
    )

    prepared = await prepare_refill_plan(
        test_session,
        reservoir_id=reservoir.id,
        target_tank_id=tank.id,
        start_level_percent=25.0,
        end_level_percent=70.0,
        started_at=started_at,
        completed_at=completed_at,
        trigger=RefillTrigger.AUTOMATIC,
        status=ExecutionStatus.COMPLETED,
    )

    assert prepared.reservoir_id == reservoir.id

    assert (
        prepared.target_tank_id
        == tank.id
    )

    assert prepared.system_id == system.id

    assert (
        prepared.plan.start_level_percent
        == pytest.approx(25.0)
    )

    assert (
        prepared.plan.end_level_percent
        == pytest.approx(70.0)
    )

    assert (
        prepared.plan.level_change_percent
        == pytest.approx(45.0)
    )

    assert (
        prepared.plan.duration_seconds
        == pytest.approx(60.0)
    )

    assert (
        prepared.plan.trigger
        == RefillTrigger.AUTOMATIC
    )

    assert (
        prepared.plan.status
        == ExecutionStatus.COMPLETED
    )


async def test_prepare_refill_plan_rejects_invalid_context(
    test_session,
):
    system = await create_system(
        test_session
    )

    reservoir = await create_reservoir(
        test_session,
        system,
    )

    tank = await create_tank(
        test_session,
        system,
        is_active=False,
    )

    started_at = datetime.now(
        timezone.utc
    )

    with pytest.raises(
        RefillCalculationError,
        match="Target tank is inactive",
    ):
        await prepare_refill_plan(
            test_session,
            reservoir_id=reservoir.id,
            target_tank_id=tank.id,
            start_level_percent=20.0,
            end_level_percent=20.0,
            started_at=started_at,
            completed_at=None,
            trigger=RefillTrigger.AUTOMATIC,
            status=ExecutionStatus.RUNNING,
        )


async def test_prepare_refill_plan_rejects_invalid_event_lifecycle(
    test_session,
):
    system = await create_system(
        test_session
    )

    reservoir = await create_reservoir(
        test_session,
        system,
    )

    tank = await create_tank(
        test_session,
        system,
    )

    started_at = datetime.now(
        timezone.utc
    )

    with pytest.raises(
        RefillCalculationError,
        match=(
            "Terminal refill status requires "
            "a completion time"
        ),
    ):
        await prepare_refill_plan(
            test_session,
            reservoir_id=reservoir.id,
            target_tank_id=tank.id,
            start_level_percent=20.0,
            end_level_percent=70.0,
            started_at=started_at,
            completed_at=None,
            trigger=RefillTrigger.AUTOMATIC,
            status=ExecutionStatus.COMPLETED,
        )