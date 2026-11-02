from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"


class SensorType(str, Enum):
    PH = "ph"
    WATER_TEMPERATURE = "water_temperature"
    TDS = "tds"
    WATER_LEVEL = "water_level"
    AIR_TEMPERATURE = "air_temperature"
    HUMIDITY = "humidity"


class MeasurementType(str, Enum):
    PH = "ph"
    TEMPERATURE = "temperature"
    TDS = "tds"
    LEVEL = "level"
    HUMIDITY = "humidity"


class LocationType(str, Enum):
    SYSTEM = "system"
    TANK = "tank"
    GROW_BED = "grow_bed"
    RESERVOIR = "reservoir"
    AMBIENT = "ambient"


class CalibrationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ReadingQuality(str, Enum):
    GOOD = "good"
    DEGRADED = "degraded"
    FAIL = "fail"


class ReadingSource(str, Enum):
    HARDWARE = "hardware"
    SIMULATOR = "simulator"
    OFFLINE_SYNC = "offline_sync"


class ActuatorType(str, Enum):
    FISH_FEEDER = "fish_feeder"
    WATER_PUMP = "water_pump"
    OXYGEN_PUMP = "oxygen_pump"
    INTAKE_FAN = "intake_fan"
    EXHAUST_FAN = "exhaust_fan"
    RESERVOIR_REFILL = "reservoir_refill"


class ControlMode(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SCHEDULED = "scheduled"


class ActuatorState(str, Enum):
    OFF = "off"
    ON = "on"
    ERROR = "error"
    UNKNOWN = "unknown"


class ActuatorCommandType(str, Enum):
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    SET_VALUE = "set_value"
    EMERGENCY_STOP = "emergency_stop"


class TriggerSource(str, Enum):
    MANUAL = "manual"
    AUTOMATION = "automation"
    SCHEDULE = "schedule"
    REFILL = "refill"
    SYSTEM = "system"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AutomationTriggerType(str, Enum):
    SENSOR_THRESHOLD = "sensor_threshold"
    SCHEDULE = "schedule"
    SYSTEM_EVENT = "system_event"
    MANUAL = "manual"


class FeedingEventStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RefillTrigger(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FAULT = "fault"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class SystemEventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RecommendationStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class SyncStatus(str, Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"

from sqlalchemy import Enum as SAEnum

USER_ROLE_DB = SAEnum(UserRole, name="user_role", native_enum=True)
SENSOR_TYPE_DB = SAEnum(SensorType, name="sensor_type", native_enum=True)
MEASUREMENT_TYPE_DB = SAEnum(MeasurementType, name="measurement_type", native_enum=True)
LOCATION_TYPE_DB = SAEnum(LocationType, name="location_type", native_enum=True)
CALIBRATION_STATUS_DB = SAEnum(CalibrationStatus, name="calibration_status", native_enum=True)
READING_QUALITY_DB = SAEnum(ReadingQuality, name="reading_quality", native_enum=True)
READING_SOURCE_DB = SAEnum(ReadingSource, name="reading_source", native_enum=True)
ACTUATOR_TYPE_DB = SAEnum(ActuatorType, name="actuator_type", native_enum=True)
CONTROL_MODE_DB = SAEnum(ControlMode, name="control_mode", native_enum=True)
ACTUATOR_STATE_DB = SAEnum(ActuatorState, name="actuator_state", native_enum=True)
ACTUATOR_COMMAND_TYPE_DB = SAEnum(ActuatorCommandType, name="actuator_command_type", native_enum=True)
TRIGGER_SOURCE_DB = SAEnum(TriggerSource, name="trigger_source", native_enum=True)
EXECUTION_STATUS_DB = SAEnum(ExecutionStatus, name="execution_status", native_enum=True)
AUTOMATION_TRIGGER_TYPE_DB = SAEnum(AutomationTriggerType, name="automation_trigger_type", native_enum=True)
FEEDING_EVENT_STATUS_DB = SAEnum(FeedingEventStatus, name="feeding_event_status", native_enum=True)
REFILL_TRIGGER_DB = SAEnum(RefillTrigger, name="refill_trigger", native_enum=True)
ALERT_SEVERITY_DB = SAEnum(AlertSeverity, name="alert_severity", native_enum=True)
ALERT_STATUS_DB = SAEnum(AlertStatus, name="alert_status", native_enum=True)
SYSTEM_EVENT_SEVERITY_DB = SAEnum(SystemEventSeverity, name="system_event_severity", native_enum=True)
RECOMMENDATION_STATUS_DB = SAEnum(RecommendationStatus, name="recommendation_status", native_enum=True)
SYNC_STATUS_DB = SAEnum(SyncStatus, name="sync_status", native_enum=True)
