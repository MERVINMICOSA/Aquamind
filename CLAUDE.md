# CLAUDE.md — AquaMind Project Instructions

This file provides guidance for Claude Code sessions working on the AquaMind project. Read this file at the start of every session.

---

## 🎯 Project Purpose

AquaMind is a thesis prototype for a **Smart Aquaponics Monitoring and Automation System** running on Raspberry Pi 5. It monitors water quality (pH, temperature, TDS, water level) and environmental conditions (air temperature, humidity), and controls actuators (fish feeder, pumps, fans, refill mechanism) through a React/TypeScript web interface backed by FastAPI and PostgreSQL.

---

## 🏗️ Architecture Rules

### Core Principles
1. **Raspberry Pi 5 is the physical controller** — All hardware interaction happens here
2. **Backend is the controlled bridge** — Web app → Backend → Hardware Abstraction Layer → Hardware
3. **Frontend NEVER accesses GPIO directly** — All hardware commands go through backend API
4. **Hardware Abstraction Layer (HAL) is mandatory** — Sensors/actuators are replaceable without rewriting application logic
5. **Simulator-first development** — Complete software prototype works with simulator before hardware integration
6. **Admin-only role for thesis prototype** — Single privileged user role

### Data Flow
```
Web UI (React) ↔ REST/WebSocket ↔ FastAPI Backend ↔ HAL ↔ Sensors/Actuators
                                      ↓
                              PostgreSQL 18
                                      ↓
                              Automation Engine
                              Alert Engine
```

---

## 🛠️ Technology Stack (Locked)

| Component | Technology | Version |
|-----------|------------|---------|
| Hardware Controller | Raspberry Pi 5 | — |
| Backend | FastAPI | Latest |
| Language | Python | 3.11+ |
| Frontend | React + TypeScript | 18+ |
| Build Tool | Vite | Latest |
| Database | PostgreSQL | 18 |
| Real-time | WebSocket | Native FastAPI |
| Auth | JWT | HS256 |
| Testing | pytest / Vitest / Playwright | Latest |

**Do not introduce new frameworks or languages without explicit approval.**

---

## 📝 Coding Principles

1. **Type safety everywhere** — Python type hints, TypeScript strict mode
2. **Async/await in backend** — FastAPI is async-first
3. **Repository pattern** — Database access through repositories, not raw ORM in routes
4. **Dependency injection** — Use FastAPI's `Depends` for services, database sessions, hardware clients
5. **Configuration via environment** — No hardcoded values, use Pydantic Settings
6. **Explicit error handling** — Custom exceptions, proper HTTP status codes
7. **Structured logging** — JSON logs with correlation IDs
8. **API versioning** — All routes under `/api/v1/`

---

## 🔒 Security Rules

### Authentication & Authorization
- **JWT tokens only** — Access (15-30 min) + Refresh (7 days)
- **Admin-only role** — Thesis prototype has single `admin` role
- **Password hashing** — bcrypt with minimum 12 rounds
- **Token storage** — HttpOnly Secure cookies for web, Authorization header for API

### Hardware Safety
- **NEVER allow AI/LLM to directly control actuators** — AI provides recommendations only
- **All actuator commands require authentication** — No anonymous control
- **Rate limiting on actuator endpoints** — Prevent accidental/intentional overload
- **Emergency stop endpoint** — Immediately disables all actuators
- **Actuator state validation** — Confirm current state before commanding changes

### Secrets Management
- **NEVER commit `.env` files** — Use `.env.example` as template
- **NEVER log secrets** — Sanitize logs
- **Rotate keys on compromise** — Document rotation procedure
- **Database passwords** — Strong, unique, stored only in environment

### API Security
- **CORS restricted** — Only frontend origin in production
- **Rate limiting** — Per-IP and per-user limits
- **Input validation** — Pydantic models on all endpoints
- **SQL injection prevention** — SQLAlchemy ORM, parameterized queries only

---

## 🗄️ Database Rules

1. **Migrations only** — Never modify schema directly; use Alembic
2. **Naming conventions** — snake_case tables/columns, plural table names
3. **Indexes on foreign keys** — Always index FK columns
4. **Soft deletes** — Use `deleted_at` timestamp, not hard deletes
5. **Audit trails** — `created_at`, `updated_at` on all tables
6. **Time-series data** — Sensor readings in partitioned tables (future)
7. **Connection pooling** — Configure pool size for expected load

---

## 🌐 API Rules

### REST Conventions
- **Resource-based URLs** — `/api/v1/sensors`, `/api/v1/actuators`
- **HTTP verbs** — GET, POST, PUT, PATCH, DELETE used correctly
- **Status codes** — 200, 201, 204, 400, 401, 403, 404, 409, 422, 500
- **Pagination** — Cursor-based for lists, `limit`/`offset` max 100
- **Filtering/sorting** — Query params: `?sort=-created_at&ph_min=6.5`

### WebSocket
- **Endpoint** — `/ws` with token authentication
- **Message format** — JSON with `type`, `payload`, `timestamp`
- **Heartbeat** — Ping/pong every 30 seconds
- **Reconnection** — Client handles exponential backoff

### Error Responses
```json
{
  "error": "validation_error",
  "message": "Human-readable description",
  "details": [{"field": "ph", "issue": "must be between 0 and 14"}],
  "request_id": "uuid"
}
```

---

## 🧪 Testing Requirements

### Coverage Targets
- **Backend**: ≥ 80% unit + integration
- **Frontend**: ≥ 70% component + integration
- **E2E**: Critical user flows (login, feeding config, emergency stop)

### Test Organization
```
tests/
├── backend/
│   ├── unit/          # Pure logic, no I/O
│   ├── integration/   # Database, HAL, API
│   └── fixtures/
├── frontend/
│   ├── unit/          # Components, hooks, utils
│   ├── integration/   # API mocking, routing
│   └── e2e/           # Playwright scenarios
└── hardware/          # Simulator validation
```

### Hardware Simulator Tests
- Validate simulator produces realistic sensor ranges
- Verify actuator state transitions
- Test failure modes (sensor disconnect, actuator jam)

---

## 🔄 Git Rules

### Branching
- `main` — Protected, production-ready
- `develop` — Integration branch (optional for thesis)
- `feature/*` — New functionality
- `fix/*` — Bug fixes
- `docs/*` — Documentation only

### Commits
- **Conventional Commits** — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- **One logical change per commit**
- **Message format**: `type(scope): description`
- **Reference issues** — `fixes #123` in footer

### History
- **No force push to main**
- **Squash merge features** — Clean history
- **Keep commits atomic** — Revertible individually

---

## ⚠️ Hard Constraints (NEVER VIOLATE)

| Rule | Description |
|------|-------------|
| **No ESP32** | Raspberry Pi 5 only — never reintroduce ESP32 |
| **No Misting** | Misting system was removed — never add it back |
| **No AI Actuator Control** | AI/analytics = recommendations only |
| **No Direct GPIO** | Frontend never touches hardware |
| **No Hardcoded Secrets** | All config via environment |
| **No Schema Changes Without Migration** | Alembic only |
| **No Framework Additions** | Stack is locked |

---

## 📋 Before Making Major Changes

1. **Read `SYSTEM_BLUEPRINT.md`** — Understand full architecture
2. **Check this `CLAUDE.md`** — Follow all rules
3. **Verify against thesis requirements** — Don't drift from scope
4. **Consider hardware abstraction** — Will this break HAL?
5. **Consider offline operation** — Does this require internet?
6. **Get approval for architectural changes** — Document rationale

---

## 🚀 Development Workflow

### Starting a Session
```bash
# 1. Read SYSTEM_BLUEPRINT.md and CLAUDE.md
# 2. Check current git status
# 3. Review any open issues/tasks
```

### Making Changes
1. Create feature branch
2. Write tests first (TDD preferred)
3. Implement with type safety
4. Run tests locally
5. Update documentation if needed
6. Create PR with description

### Hardware Development
- **Always test with simulator first**
- **Validate HAL interface compliance**
- **Document pin mappings in `.env.example`**
- **Never commit hardware-specific code without abstraction**

---

## 📚 Reference Documents

- `SYSTEM_BLUEPRINT.md` — Complete architecture specification
- `.env.example` — Configuration reference
- `README.md` — Project overview
- `docs/` — Additional technical docs (created as needed)

---

## 🆘 Emergency Procedures

### If Hardware Acts Unexpectedly
1. Hit **Emergency Stop** in web UI (disables all actuators)
2. Check backend logs for last commands
3. Verify simulator vs hardware mode
4. Document incident in `docs/incidents/`

### If Security Issue Found
1. Rotate affected secrets immediately
2. Audit access logs
3. Document in `docs/security/`
4. Notify thesis supervisor

---

*This document is the source of truth for development practices. When in doubt, refer to SYSTEM_BLUEPRINT.md and the thesis requirements.*