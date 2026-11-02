# AquaMind Phase 4 Workflow

## Purpose

Phase 4 is executed without depending on Claude Code for implementation.

ChatGPT produces the project artifacts. Claude Code is optional and is used only for independent checking/review.

## Phase 4A — Database Design

**Output**
- `docs/DATABASE_DESIGN.md`
- `docs/PHASE_4A_REVIEW.md`

**Gate**
- Architecture consistency reviewed.
- No database implementation performed.

## Phase 4B — SQLAlchemy Models

**Output**
- SQLAlchemy declarative base
- enums/types
- all database models
- model relationships
- database-session foundation
- unit tests for model constraints/relationships

**Gate**
- Model structure matches `DATABASE_DESIGN.md`.
- No Alembic migration is generated until 4B is accepted.

## Phase 4C — Alembic / PostgreSQL

**Output**
- Alembic configuration
- initial migration
- PostgreSQL schema constraints/indexes
- migration verification

**Gate**
- upgrade/downgrade validation passes.
- Schema matches Phase 4A and 4B.

## Phase 4D — Repositories

**Output**
- repository/data-access layer
- sensor-reading queries
- actuator/event persistence
- feeding/refill/alert/automation/audit/sync persistence
- repository tests

**Gate**
- Business logic remains out of repositories.
- Queries respect append-only/history requirements.

## Phase 4E — Backend / API

**Output**
- FastAPI application structure
- schemas
- services
- API endpoints
- authentication/authorization
- WebSocket integration
- synchronization services

**Gate**
- API behavior matches the architecture and database model.
- AI remains advisory.

## Phase 4F — Database / Backend Validation

**Output**
- integration tests
- migration tests
- synchronization/idempotency tests
- retention/index checks
- critical safety-path tests

**Gate**
- Phase 4 database/backend layer is complete and ready for later frontend/hardware integration.

## Operating rule

At every phase:

1. Implement the phase's files.
2. Run validation/tests appropriate to that phase.
3. Review against `SYSTEM_BLUEPRINT.md`, `CLAUDE.md`, and `README.md`.
4. Do not silently change architecture.
5. Record unresolved decisions.
6. Stop at the phase gate before proceeding.

Claude Code may inspect and report problems, but **Claude is never a dependency for progress**.
