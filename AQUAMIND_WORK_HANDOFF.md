# AquaMind — ChatGPT Work Handoff

Updated: 2026-09-26
Project root: `C:\Projects\aquamind`

## Purpose

This is the authoritative continuation checkpoint for AquaMind. Continue from the current checkpoint. Do not restart architecture/design work or revalidate locked phases unless a later integration exposes a concrete defect.

## Environment

- Windows laptop / PowerShell
- Backend: `C:\Projects\aquamind\backend`
- Frontend: `C:\Projects\aquamind\frontend`
- Python venv: `C:\Projects\aquamind\.venv`
- Backend: FastAPI + SQLAlchemy async + PostgreSQL
- Frontend: React + TypeScript + Vite + Vitest + Testing Library
- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`
- API: `http://127.0.0.1:8000/api/v1`
- `HARDWARE_ENABLED=false`

## Runtime

Backend:

```powershell
Set-Location C:\Projects\aquamind\backend
$env:HARDWARE_ENABLED="false"

uvicorn app.main:app `
    --host 127.0.0.1 `
    --port 8000 `
    --reload
```

Frontend:

```powershell
Set-Location C:\Projects\aquamind\frontend
npm run dev
```

## Working rules

- Inspect only files needed for the current task.
- Targeted test/check first.
- Diagnose the exact failing layer.
- Make the smallest correct change.
- Rerun the targeted test.
- Run full suites only at logical lock/cross-stack checkpoints.
- Preserve known-good code and locked checkpoints.
- Reuse existing services, hooks, schemas, models, and API contracts.
- Do not duplicate canonical history/event models.
- Do not reopen Phase 6 business logic, Phase 8 runtime orchestration, or Phase 9 HAL/deployment preparation without a concrete integration defect.
- Prefer complete updated files when partial edits would be confusing.
- Use Windows PowerShell.
- Ignore Vitest repeated-jsdom performance notes unless there is an actual test defect.
- Do not invent GPIO pins, relay polarity, ADC channels, sensor models, wiring, thresholds, sampling tolerances, timings, or physical execution state.
- Simulator/database state is never proof of physical hardware execution.

## COMPLETE + LOCKED

- Phases 1–9
- Phase 10A — Frontend Foundation
- Phase 10B — Authentication & Authorization UI
- Phase 10C — Dashboard / Telemetry
- Phase 10D — Sensors
- Phase 10E — Actuators
- Phase 10F — Alerts
- Phase 10G — Feeding
- Phase 10H — Automation
- Phase 10I — Settings
- Phase 10J — Refill Visibility

## Current baselines

### Backend

```text
593/593 passed
```

### Frontend

```text
TypeScript clean
ESLint clean
34/34 test files
170/170 tests
Production build passed
Browser verification passed
```

Latest build:

```text
Vite 8.2.2
76 modules transformed
CSS 22.96 kB / 4.34 kB gzip
JS 315.82 kB / 84.71 kB gzip
```

## Phase 10H — Automation

COMPLETE + LOCKED through 10H.3.

Bounded run history:

```text
GET /api/v1/automation-runs/history?rule_id=<uuid>&limit=50&offset=0
```

- rule required
- parent validation
- strict rule filter
- deterministic `started_at DESC, id DESC`
- frontend uses 51-row lookahead for 50-row pages

Automation UI uses only the demonstrated sensor-threshold runtime shape. Do not imply unsupported schedule/system-event/manual execution behavior.

## Phase 10I — Settings

COMPLETE + LOCKED.

Real backend contract:

```text
GET /api/v1/system-settings
POST /api/v1/system-settings
PATCH /api/v1/system-settings/{id}
DELETE /api/v1/system-settings/{id}
```

- admin-only mutations
- `setting_key`: string 1..150
- `setting_value`: arbitrary string including empty
- `value_type`: free-form string 1..32
- no invented `value_type` enum
- no restore endpoint
- PATCH sends only changed fields

## Phase 10J — Refill Visibility

### 10J.1 — Bounded Refill Event History API Foundation

COMPLETE + LOCKED.

```text
GET /api/v1/refill-events/history?reservoir_id=<uuid>&limit=50&offset=0
```

Contract:

- `reservoir_id` required
- limit 1..100, default 50
- offset >=0, default 0
- missing/soft-deleted reservoir -> `404 "Reservoir not found"`
- strict reservoir filter
- deterministic `started_at DESC, id DESC`
- reuses canonical `RefillEvent`
- generic refill list unchanged
- mutation authorization unchanged

Do not reinterpret POST/PATCH `/refill-events` as human Start/Stop commands.

### 10J.2 — Read-only Refill History UI

COMPLETE + LOCKED.

Route:

```text
/refill
```

Behavior:

- sidebar entry `Refill`
- system selection
- reservoir selection
- tank-name resolution
- bounded history, page size 50
- requests 51 rows for lookahead
- Previous/Next pagination
- preserves zero/null values honestly
- no Start/Stop/Edit/Delete refill controls
- explicit disclaimer that persisted refill records do not establish physical hardware execution

Browser verification passed with current local data:

```text
/refill loaded
Refill sidebar entry active
backend online
AquaMind Test System selected
"No reservoirs configured" empty state rendered
hardware disclaimer visible
no manual refill controls exposed
```

## Refill contracts

Canonical model: `RefillEvent`.

Frontend-used fields:

```text
id
reservoir_id
target_tank_id
start_level_percent
end_level_percent
started_at
completed_at
duration_seconds
trigger
status
timeout_reason
created_at
```

Reservoir list:

```text
GET /api/v1/reservoirs?system_id=<uuid>
```

Historical visibility must not disappear merely because a non-deleted reservoir is currently inactive.

Manual refill execution remains DEFERRED until a real command/execution contract exists.

## Current protected routes

```text
/
/sensors
/sensors/:sensorId
/actuators
/actuators/:actuatorId
/feeding
/refill
/automation
/alerts
/settings
```

## Hardware boundary

Current:

```text
Windows laptop
HARDWARE_ENABLED=false
physical components not finalized
simulator/test/persisted data only
```

Do not infer physical execution from persisted state.

## CURRENT / NEXT

Do not invent the next phase name.

The immediate next action is a narrow remaining-scope inventory using the real repository and project documentation. Identify unfinished work after Phase 10J without reopening locked phases.

Run:

```powershell
Set-Location C:\Projects\aquamind

Write-Host "===== ROADMAP / TODO REFERENCES ====="

Get-ChildItem . `
    -File `
    -Recurse `
    -Include *.md,*.txt |
Select-String `
    -Pattern `
        "Phase 10", `
        "NEXT", `
        "TODO", `
        "remaining", `
        "deferred" `
    -Context 1,3

Write-Host "`n===== CURRENT FRONTEND ROUTES ====="
Get-Content .\frontend\src\app\router.tsx

Write-Host "`n===== CURRENT NAVIGATION ====="
Get-Content .\frontend\src\layouts\AppLayout.tsx
```

Use that output to name the next unfinished phase from repository evidence, not assumption.

Do not add manual refill execution unless a real command contract is found.

## Instruction to ChatGPT Work

Treat this file as authoritative.

- Do not restart earlier phases.
- Do not revalidate locked phases without a specific defect.
- Inspect real repository files when needed.
- Prefer existing contracts.
- Keep `HARDWARE_ENABLED=false` on Windows.
- Do not invent hardware.
- Preserve the 593 backend / 170 frontend baselines.
- Use focused tests first.
- Give exact PowerShell commands.
- Provide complete updated files when partial edits would be confusing.
