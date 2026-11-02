from app.db.base import Base
from app.db.enums import UserRole

# Import all model modules so SQLAlchemy registers their tables.
from app.models import actuators
from app.models import alerts
from app.models import automation
from app.models import feeding
from app.models import other
from app.models import refill
from app.models import sensors
from app.models import system


EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "aquaponics_systems",
    "system_settings",
    "tanks",
    "grow_beds",
    "reservoirs",
    "sensors",
    "sensor_readings",
    "actuators",
    "actuator_events",
    "automation_rules",
    "feeding_schedules",
    "feeding_events",
    "refill_events",
    "alert_thresholds",
    "alerts",
    "audit_logs",
    "system_events",
    "ai_recommendations",
    "sync_records",
    "fish_population_records",
    "automation_runs",
    "feeder_calibrations",
    "sensor_calibrations",
}


def test_phase_4c_expected_tables_are_registered():
    actual_tables = set(Base.metadata.tables)

    missing = EXPECTED_TABLES - actual_tables

    assert not missing, f"Missing model tables: {sorted(missing)}"


def test_phase_4c_expected_tables_are_exactly_registered():
    actual_tables = set(Base.metadata.tables)

    assert actual_tables == EXPECTED_TABLES


def test_admin_is_the_only_defined_user_role():
    assert list(UserRole) == [UserRole.ADMIN]


def test_system_setting_has_created_at():
    table = Base.metadata.tables["system_settings"]

    assert "created_at" in table.c
    assert "updated_at" in table.c
    assert "deleted_at" in table.c


def test_sensor_readings_have_expected_indexes():
    table = Base.metadata.tables["sensor_readings"]

    index_columns = {
        tuple(column.name for column in index.columns)
        for index in table.indexes
    }

    assert ("recorded_at",) in index_columns
    assert ("sensor_id", "recorded_at") in index_columns