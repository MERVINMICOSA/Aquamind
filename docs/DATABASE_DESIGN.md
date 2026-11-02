# AquaMind Database Design

**Phase:** 4A — Database Design  
**Status:** Phase 4A reviewed design baseline  
**Persistent database:** PostgreSQL 18  
**Offline buffer:** SQLite on Raspberry Pi 5

## 1. Purpose and Scope

This document defines the proposed relational database design for AquaMind, the Smart Aquaponics Monitoring and Automation System running on Raspberry Pi 5.

The database persists system configuration, aquaponics structures, sensors, readings, actuators, automation history, feeding, refill events, alerts, audit history, synchronization information, and non-safety-critical AI recommendations.

This is a design specification only. It does not create PostgreSQL tables or migrations.

## 2. Architecture

The persistent data flow is:

```text
Local Raspberry Pi 5
  SQLite offline buffer
        |
   synchronize
        v
  PostgreSQL
    |       |
  Web UI  Analytics
```

The Pi runs local hardware abstraction, automation, and alerts independently of network access. The FastAPI backend serves the web UI and synchronizes data when connectivity is available.

The frontend never accesses PostgreSQL or GPIO directly.

## 3. Design Principles

1. Sensor readings are append-only historical records.
2. Configuration is separated from execution/history.
3. Actuator executions are retained for traceability.
4. All operational records have event timestamps.
5. PostgreSQL is the persistent synchronized store.
6. SQLite is the offline operational buffer.
7. AI recommendations are separate from actuator execution.
8. AI never directly controls safety-critical hardware.
9. Settings use timestamp-based last-write-wins.
10. Sensor readings are append-only and therefore conflict-free.
11. Local actuator execution takes precedence over queued remote commands.
12. High-volume readings must be indexed and may be time-partitioned.

## 4. Proposed Tables

| Table | Purpose |
|---|---|
| `users` | Admin account(s) |
| `refresh_tokens` | Hashed JWT refresh-token persistence/revocation |
| `system_settings` | Timestamped system configuration/settings |
| `aquaponics_systems` | Top-level AquaMind installation |
| `tanks` | Fish/water tanks |
| `grow_beds` | Plant growing areas |
| `reservoirs` | Refill-water storage |
| `sensors` | Sensor definitions |
| `sensor_calibrations` | Sensor calibration history and verification |
| `sensor_readings` | Timestamped measurements |
| `actuators` | Controllable devices |
| `actuator_events` | Actual actuator executions |
| `automation_rules` | Automatic-control rules |
| `automation_runs` | Rule execution history |
| `feeding_schedules` | Scheduled feeding |
| `feeder_calibrations` | Feeder calibration history |
| `feeding_events` | Actual feeding operations |
| `fish_population_records` | Fish count/biomass history |
| `refill_events` | Water refill operations |
| `alert_thresholds` | Warning/critical limits |
| `alerts` | Alert lifecycle |
| `system_events` | Operational/system-health events |
| `ai_recommendations` | Advisory AI/analytics results |
| `audit_logs` | Administrator/configuration history |
| `sync_records` | SQLite-to-PostgreSQL synchronization |

## 5. Core System Tables

### `users`

- `id` UUID primary key
- `username` unique
- `password_hash`
- `role` (currently `admin` only)
- `is_active`
- `created_at`
- `updated_at`
- `last_login_at`

The current architecture specifies an **admin-only role**. A general role hierarchy is deferred.

### `refresh_tokens`

- `id` UUID primary key
- `user_id` FK -> `users.id`
- `token_hash`
- `issued_at`
- `expires_at`
- `revoked_at`
- `created_at`

Refresh tokens are stored hashed and are revocable, matching the JWT security requirements.

### `system_settings`

- `id` UUID primary key
- `system_id` FK -> `aquaponics_systems.id`
- `setting_key` unique within system
- `setting_value`
- `value_type`
- `updated_at`
- `updated_by_user_id` FK
- `deleted_at`

Settings use timestamp-based last-write-wins during synchronization.

### `aquaponics_systems`

- `id` UUID primary key
- `name`
- `description`
- `timezone`
- `is_active`
- `created_at`
- `updated_at`

### `tanks`

- `id` UUID primary key
- `system_id` FK -> `aquaponics_systems.id`
- `name`
- `capacity_liters`
- `species`
- `is_active`
- `created_at`
- `updated_at`
- `deleted_at`

One system has many tanks.

### `grow_beds`

- `id` UUID primary key
- `system_id` FK
- `name`
- `crop_type`
- `capacity_description`
- `is_active`
- `created_at`
- `updated_at`
- `deleted_at`

One system has many grow beds. Lettuce is a current target crop, but the schema does not hard-code it.

### `reservoirs`

- `id` UUID primary key
- `system_id` FK
- `name`
- `capacity_liters`
- `is_active`
- `created_at`
- `updated_at`
- `deleted_at`

A reservoir is distinct from the target tank because refill requires a reservoir-water check.

## 6. Sensors and Readings

### `sensors`

- `id` UUID primary key
- `system_id` FK
- `name`
- `sensor_type`
- `measurement_type`
- `location_type`
- `location_id`
- `unit`
- `hardware_identifier`
- `is_simulated`
- `is_enabled`
- `sampling_interval_seconds`
- `calibration_status`
- `created_at`
- `updated_at`

Current measurements are pH, water temperature, TDS, water level, air temperature, and humidity.

### `sensor_calibrations`

- `id` UUID primary key
- `sensor_id` FK -> `sensors.id`
- `offset`
- `factor`
- `calibration_data`
- `performed_at`
- `verified_by_user_id` FK
- `status`
- `notes`
- `created_at`

Calibration history is retained separately from the sensor definition. Sensor calibration requires human verification.

### `sensor_readings`

- `id` UUID/time-sortable primary key
- `sensor_id` FK -> `sensors.id`
- `recorded_at` timestamptz
- `value_numeric`
- `unit`
- `quality_status`
- `source`
- `sequence_number`
- `created_at`

Readings are append-only.

Recommended indexes:

```text
(sensor_id, recorded_at DESC)
(recorded_at DESC)
```

`source` can distinguish hardware, simulator, or offline synchronization.

This is the expected highest-volume table and may be partitioned by time after actual data volume is known.

## 7. Actuators and Events

### `actuators`

- `id` UUID primary key
- `system_id` FK
- `name`
- `actuator_type`
- `control_mode`
- `hardware_identifier`
- `location_type`
- `location_id`
- `is_enabled`
- `safety_config`
- `current_state`
- `current_value`
- `last_state_at`
- `created_at`
- `updated_at`
- `deleted_at`

Current actuator types are fish feeder, water pump, oxygen pump, intake fan, exhaust fan, and reservoir refill valve/solenoid.

### `actuator_events`

- `id` UUID primary key
- `actuator_id` FK
- `command_type`
- `requested_value`
- `actual_value`
- `started_at`
- `completed_at`
- `duration_ms`
- `trigger_source`
- `status`
- `fault_code`
- `error_message`
- `created_at`

The database records what actually happened. AI is not a direct actuator trigger.

## 8. Automation

### `automation_rules`

- `id` UUID primary key
- `system_id` FK
- `name`
- `description`
- `trigger_type`
- `condition_definition`
- `action_definition`
- `enabled`
- `priority`
- `cooldown_seconds`
- `created_at`
- `updated_at`

Rule definitions are interpreted by the application/service layer, not executed as arbitrary database code.

### `automation_runs`

- `id` UUID primary key
- `rule_id` FK
- `started_at`
- `completed_at`
- `trigger_value`
- `status`
- `result_summary`
- `error_message`

One rule has many runs.

## 9. Feeding

### `feeding_schedules`

- `id` UUID primary key
- `system_id` FK
- `actuator_id` FK to feeder
- `name`
- `schedule_expression`
- `enabled`
- `max_per_feed_grams`
- `created_at`
- `updated_at`

### `feeder_calibrations`

- `id` UUID primary key
- `actuator_id` FK
- `run_count`
- `measured_seconds`
- `measured_grams`
- `grams_per_second`
- `calibration_method`
- `performed_at`
- `verified_by_user_id`
- `notes`

The architecture specifies repeated dispense tests and use of the median calibration result.

### `fish_population_records`

- `id` UUID primary key
- `tank_id` FK
- `species`
- `count`
- `estimated_biomass_grams`
- `effective_at`
- `recorded_by_user_id`
- `notes`

Population changes are historical records because feeding calculations depend on population configuration.

### `feeding_events`

- `id` UUID primary key
- `schedule_id` FK, nullable for manual feeds
- `actuator_event_id` FK
- `tank_id` FK
- `amount_grams`
- `duration_seconds`
- `calculated_from_biomass`
- `calibration_id` FK
- `executed_at`
- `status`
- `notes`

The architecture requires recording schedule, amount, duration, and timestamp.

Safety limits include maximum daily feed, maximum single-feed duration, minimum cooldown, and recalculation after population changes. These are application safety rules, never AI decisions.

## 10. Water Refill

### `refill_events`

- `id` UUID primary key
- `reservoir_id` FK
- `target_tank_id` FK
- `start_level_percent`
- `end_level_percent`
- `started_at`
- `completed_at`
- `duration_seconds`
- `trigger`
- `status`
- `timeout_reason`
- `created_at`

The blueprint requires start/end level, duration, and trigger information.

Current refill logic includes critical low <15%, warning low <25%, optimal 40–80%, critical high >95%, maximum refill duration of 5 minutes, reservoir-level checking, and a 30-minute automatic-refill cooldown.

## 11. Alerts

### `alert_thresholds`

- `id` UUID primary key
- `sensor_type`
- `measurement_type`
- `warning_low`
- `warning_high`
- `critical_low`
- `critical_high`
- `cooldown_seconds`
- `enabled`
- `updated_by_user_id`
- `updated_at`

Current critical limits documented by the architecture:

| Parameter | Low | High |
|---|---:|---:|
| pH | <6.0 | >8.0 |
| Water temperature | <15°C | >32°C |
| TDS | — | >1200 ppm |
| Water level | <15% | >95% |
| Air temperature | <15°C | >35°C |
| Humidity | <30% | >90% |

### `alerts`

- `id` UUID primary key
- `system_id` FK
- `sensor_id` FK, nullable
- `actuator_id` FK, nullable
- `alert_type`
- `severity`
- `message`
- `trigger_value`
- `threshold_id` FK
- `status`
- `created_at`
- `acknowledged_at`
- `acknowledged_by_user_id`
- `resolved_at`
- `resolution_reason`

Lifecycle:

```text
ACTIVE -> ACKNOWLEDGED -> RESOLVED
```

The condition can automatically resolve an alert. Default cooldown is 15 minutes per alert type plus sensor/actuator.

## 12. System Events

### `system_events`

Stores events such as:

- backend start/stop
- local automation start/stop
- offline/online transitions
- simulator mode changes
- synchronization completion/failure
- hardware faults

Columns:

- `id`
- `system_id` FK
- `event_type`
- `severity`
- `message`
- `metadata`
- `occurred_at`

This keeps operational events separate from sensor measurements.

## 13. AI / Analytics

### `ai_recommendations`

- `id` UUID primary key
- `system_id` FK
- `recommendation_type`
- `title`
- `description`
- `evidence`
- `generated_at`
- `status`
- `reviewed_by_user_id`
- `reviewed_at`
- `approval_notes`
- `applied_action_reference`

Permitted AI functions are trend analysis, anomaly detection, recommendations, predictive maintenance, and optimization.

AI is prohibited from directly commanding actuators, overriding safety thresholds, disabling emergency stop, changing automation rules without admin approval, or calibrating sensors without human verification.

## 14. Audit

### `audit_logs`

- `id` UUID primary key
- `user_id` FK
- `action`
- `entity_type`
- `entity_id`
- `old_value`
- `new_value`
- `source`
- `created_at`

Important audited actions include threshold changes, automation changes, feeding schedule changes, calibration approval, population changes, manual actuator commands, alert acknowledgement, AI recommendation approval/rejection, and system configuration changes.

Audit logs are append-only.

## 15. Synchronization

### `sync_records`

- `id` UUID primary key
- `source_device_id`
- `entity_type`
- `local_record_id`
- `remote_record_id`
- `event_timestamp`
- `synced_at`
- `sync_status`
- `error_message`

Synchronization must preserve original event timestamps and avoid duplicates on retry.

Conflict policy from the architecture:

- settings: timestamp-based last-write-wins
- sensor readings: append-only
- actuator commands: local execution takes precedence; remote commands queue

## 16. Relationships

```text
aquaponics_systems
  ├── tanks
  │     └── fish_population_records
  ├── grow_beds
  ├── reservoirs
  │     └── refill_events
  ├── sensors
  │     └── sensor_readings
  ├── actuators
  │     ├── actuator_events
  │     └── feeder_calibrations
  ├── automation_rules
  │     └── automation_runs
  ├── feeding_schedules
  │     └── feeding_events
  ├── alerts
  ├── system_events
  ├── ai_recommendations
  ├── audit_logs
  └── sync_records
```

Important cardinalities:

- system 1:N tanks
- system 1:N grow beds
- system 1:N reservoirs
- system 1:N sensors
- sensor 1:N readings
- system 1:N actuators
- actuator 1:N actuator events
- actuator 1:N calibrations
- rule 1:N automation runs
- schedule 1:N feeding events
- tank 1:N population records
- sensor/actuator 1:N alerts

## 17. Data Lifecycle and Retention

Mutable configuration/entity tables use `deleted_at` where soft deletion is required by the architecture. Historical/event tables remain append-only and are not treated as ordinary soft-deleted entities.

Retention targets from the blueprint:

- `sensor_readings`: 1 year
- `alerts`: 30 days
- audit and operational history: retained according to thesis/evidence requirements unless a later policy is approved

Retention enforcement is an implementation concern for Phase 4B/4C; Phase 4A only defines the required policy.

## 17. Timestamp Strategy

Use PostgreSQL `timestamptz`.

Distinguish:

- `recorded_at` / `occurred_at`: when the event actually happened
- `created_at`: when its database record was persisted
- `synced_at`: when an offline record reached PostgreSQL

This is necessary for offline operation.

## 18. Security

- Store password hashes, never plaintext passwords.
- Keep credentials in environment configuration, not source code.
- Use least-privilege database credentials.
- Use parameterized ORM/database operations.
- Keep audit records for important admin actions.
- Do not allow frontend-to-database access.
- Do not allow frontend-to-GPIO access.

## 19. Legacy Components Excluded

The following original-proposal components are intentionally excluded from the current schema:

- **ESP32:** replaced by Raspberry Pi 5.
- **Misting system:** explicitly removed.
- **General multi-user roles:** current architecture specifies admin-only.
- **AI direct actuator control:** explicitly prohibited.
- **Cloud-dependent operation:** replaced by offline-capable local operation with SQLite buffering and PostgreSQL synchronization.

## 20. Important Design Decisions

1. PostgreSQL is the persistent synchronized store.
2. SQLite provides the Pi offline buffer.
3. Sensor readings are append-only.
4. Configuration is separate from execution history.
5. Actuator execution is auditable.
6. Feeding calibration, population, schedules, and actual events are separate records.
7. Alerts retain their lifecycle.
8. AI recommendations are advisory records and do not directly control hardware.
9. No ESP32-specific schema is required.
10. No misting-specific schema is required.

## 21. Assumptions and Reconciliation Notes

The following remain implementation-level decisions rather than architecture changes:

1. UUIDs are preferred application identifiers.
2. Decimal measurements use PostgreSQL `numeric` where appropriate.
3. JSONB may be used for flexible metadata/evidence/rule definitions.
4. One primary AquaMind installation is expected for the thesis prototype.
5. Sensor readings are retained for 1 year and alerts for 30 days, matching the blueprint.
6. Monthly sensor-reading partitioning is the current target, subject to confirming actual volume.
7. Exact SQLite/PostgreSQL synchronization identifiers need implementation-level definition.

The blueprint's compact database overview is treated as a high-level schema summary. This Phase 4A design expands it into normalized tables where needed for auditability, calibration history, synchronization, and authentication persistence. This is a refinement, not an architectural change.

## 22. Not Yet Implemented

This design does not create:

- SQLAlchemy models
- Alembic migrations
- PostgreSQL tables
- SQLite schema
- API endpoints
- repositories/services
- frontend code
- hardware drivers
- simulator implementation
- tests

Those belong to later implementation phases. Claude Code is not a required implementation dependency; it may be used only as an independent reviewer/checker.

## 23. Remaining Review Items

Before implementation, review:

1. exact table/column naming
2. sensor/actuator location modeling
3. final monthly partition implementation and retention enforcement
4. SQLite/PostgreSQL synchronization identifiers and idempotency key
5. automation-rule condition/action representation
6. exact settings value serialization/type rules
7. whether `deleted_at` is required on every mutable entity or only configuration entities

### Blueprint items explicitly reconciled

- PostgreSQL 18 remains the persistent store; SQLite remains the Pi offline buffer.
- Raspberry Pi 5 remains the execution platform; ESP32 is excluded.
- Misting is excluded.
- AI remains advisory and requires admin review before an approved action can be applied.
- Frontend access remains through the backend; no direct database or GPIO access is introduced.
- The blueprint's `actuator_states` concept is represented by current-state columns on `actuators` plus immutable `actuator_events` history.
- The blueprint's `calibration_data` concept is represented by normalized `sensor_calibrations` and `feeder_calibrations` history.
- The blueprint's `system_settings` and hashed refresh-token persistence are explicitly represented.

## 24. Phase 4A Completion Criterion

Phase 4A is complete when this document has been reviewed against `SYSTEM_BLUEPRINT.md`, the table relationships and exclusions are accepted, assumptions are acknowledged, and no contradiction with the Raspberry Pi 5 architecture remains.

Only then should SQLAlchemy models and Alembic migrations be implemented.
