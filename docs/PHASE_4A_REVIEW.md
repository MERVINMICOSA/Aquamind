# AquaMind Phase 4A Review

## Review basis

Reviewed against the Phase 3 architecture specification and the existing Phase 4A database-design draft.

## Status

**Phase 4A design is ready to proceed to implementation review, with the remaining items below treated as implementation-level decisions rather than blockers.**

## Architecture constraints confirmed

- Raspberry Pi 5 is the execution platform.
- ESP32 is excluded.
- Misting is excluded.
- PostgreSQL 18 is the persistent synchronized store.
- SQLite is the Raspberry Pi offline buffer.
- Sensor readings are append-only.
- Frontend access goes through the backend; no direct PostgreSQL or GPIO access.
- AI is advisory only and cannot directly command safety-critical hardware.
- Feeding, refill, alerts, automation, audit, synchronization, and actuator execution are represented.

## Corrections/reconciliations made

1. Added persistent system settings because the architecture explicitly defines settings and timestamp-based last-write-wins.
2. Added hashed refresh-token persistence because the JWT architecture requires refresh-token storage and revocation.
3. Added sensor calibration history because calibration is a first-class architecture requirement.
4. Clarified the actuator-state design: current state belongs to the actuator definition while `actuator_events` retains execution history.
5. Reconciled retention with the architecture: sensor readings = 1 year; alerts = 30 days.
6. Documented soft-delete/lifecycle handling for mutable entities.
7. Clarified that the normalized Phase 4A schema expands the blueprint's compact high-level table summary without changing the architecture.

## Remaining implementation-level decisions

- Exact SQLite/PostgreSQL idempotency identifiers.
- Final partition implementation and retention enforcement.
- Exact automation rule condition/action serialization.
- Final sensor/actuator location model.
- Exact settings serialization/type rules.
- Final scope of `deleted_at`.

## Phase boundary

Phase 4A does **not** implement SQLAlchemy, Alembic, PostgreSQL tables, SQLite schema, API endpoints, repositories, services, frontend code, hardware drivers, or tests.

Those begin only in the subsequent implementation phases.

## New workflow

Claude Code is optional and checker-only. The primary implementation work is produced and reviewed here. Claude may later be given read-only/checking tasks, but a Claude API failure must never block progress.
