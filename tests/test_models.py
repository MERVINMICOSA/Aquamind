from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import UserRole
from app.models import (
    Actuator,
    ActuatorEvent,
    AquaponicsSystem,
    Sensor,
    SensorReading,
)
from app.db.enums import ActuatorState, ActuatorType


def test_all_phase_4a_tables_are_registered():
    expected = {
        "users", "refresh_tokens", "system_settings", "aquaponics_systems",
        "tanks", "grow_beds", "reservoirs", "sensors", "sensor_calibrations",
        "sensor_readings", "actuators", "actuator_events", "automation_rules",
        "automation_runs", "feeding_schedules", "feeder_calibrations",
        "feeding_events", "fish_population_records", "refill_events",
        "alert_thresholds", "alerts", "system_events", "ai_recommendations",
        "audit_logs", "sync_records",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_system_sensor_reading_relationship():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        system = AquaponicsSystem(name="Test System", timezone="Asia/Manila")
        sensor = Sensor(
            system=system,
            name="pH Sensor",
            sensor_type="ph",
            measurement_type="ph",
            location_type="tank",
            unit="pH",
            sampling_interval_seconds=30,
            calibration_status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        reading = SensorReading(
            sensor=sensor,
            recorded_at=datetime.now(timezone.utc),
            value_numeric=7.1,
            unit="pH",
            quality_status="good",
            source="simulator",
        )
        session.add(system)
        session.commit()

        loaded = session.scalar(select(Sensor).where(Sensor.id == sensor.id))
        assert loaded is not None
        assert loaded.system.id == system.id
        assert loaded.readings[0].id == reading.id


def test_actuator_event_is_linked_to_actuator():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        system = AquaponicsSystem(name="Test System", timezone="Asia/Manila")
        actuator = Actuator(
            system=system,
            name="Feeder",
            actuator_type=ActuatorType.FISH_FEEDER,
            control_mode="manual",
            current_state=ActuatorState.OFF,
        )
        event = ActuatorEvent(
            actuator=actuator,
            command_type="activate",
            trigger_source="manual",
            status="completed",
            started_at=datetime.now(timezone.utc),
        )
        session.add(system)
        session.commit()

        assert event.actuator_id == actuator.id
        assert actuator.events[0].id == event.id


def test_admin_is_the_only_defined_user_role():
    assert UserRole.ADMIN.value == "admin"
    assert [role.value for role in UserRole] == ["admin"]
