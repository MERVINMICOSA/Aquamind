# SYSTEM_BLUEPRINT.md — AquaMind Architecture Specification

**Version:** 1.0  
**Status:** Draft — Phase 1 Foundation  
**Last Updated:** 2026-08-08

---

### Architecture addendum — 2026-11-03

The Raspberry Pi 5 remains AquaMind's only actuator execution controller. Following the user's updated requirement, a **sensor-only ESP32 DevKit** may transmit versioned `aquamind_sensor` JSON packets over a physical USB serial connection to the Raspberry Pi FastAPI backend. Raw packets and calibration flags are preserved in a separate history table, and the dashboard shows the latest packet and recent history. ESP32 sensor telemetry does not authorize or imply direct relay/pump control. Unverified pH/TDS estimates must not be promoted to the canonical `sensor_readings` path or affect water-quality automation. See `docs/ESP32_TELEMETRY.md` for the request format, security boundary, and setup.

---

## 1. Project Overview

AquaMind is a thesis prototype for a **Smart Aquaponics Monitoring and Automation System** running on **Raspberry Pi 5**. The system provides comprehensive monitoring of water quality and environmental conditions, with automated and remote control of actuators for feeding, circulation, aeration, ventilation, and water level management.

### 1.1 Thesis Alignment

This prototype demonstrates:
- **IoT sensor integration** with hardware abstraction for sensor/actuator replaceability
- **Edge computing** on Raspberry Pi 5 with offline/local operation capability
- **Real-time web interface** with authenticated remote control
- **Automation engine** for scheduled and rule-based actuator control
- **Alert engine** for threshold-based notifications
- **Calibrated feeding system** based on fish population and feeder characteristics

### 1.2 Confirmed Project Modifications (from Original Proposal)

| Original | Modified | Status |
|----------|----------|--------|
| ESP32 microcontroller | **Raspberry Pi 5** | ✅ Confirmed |
| Misting system included | **Misting system removed** | ✅ Confirmed |
| Monitoring-only web UI | **Interactive remote controls + local touchscreen** | ✅ Confirmed |
| No user roles | **Admin-only role** | ✅ Confirmed |
| Basic feeding | **Calibrated, configurable feeding** | ✅ Confirmed |
| No water-level automation | **Water-level monitoring + refill workflow** | ✅ Confirmed |
| Cloud-dependent | **Offline-capable local operation** | ✅ Confirmed |
| Direct GPIO access | **Hardware Abstraction Layer (HAL)** | ✅ Confirmed |
| AI actuator control | **AI = advisory only** | ✅ Confirmed |

---

## 2. Functional Requirements

### 2.1 Sensor Monitoring
| Parameter | Sensor Type | Range | Critical Thresholds |
|-----------|-------------|-------|---------------------|
| pH | Analog/I2C | 0–14 | <6.0 / >8.0 |
| Water Temperature | DS18B20 (1-Wire) | -10–50°C | <15°C / >32°C |
| TDS | Analog/I2C | 0–2000 ppm | >1200 ppm |
| Water Level | Ultrasonic/Float | 0–100% | <15% / >95% |
| Air Temperature | DHT22/I2C | -40–80°C | <15°C / >35°C |
| Humidity | DHT22/I2C | 0–100% | <30% / >90% |

### 2.2 Actuator Control
| Actuator | Type | Control Method | Safety Features |
|----------|------|----------------|-----------------|
| Fish Feeder | Servo/Stepper | Timed dispense | Calibration, max daily limit |
| Water Pump | Relay | On/Off | Dry-run protection |
| Oxygen Pump | Relay | On/Off | Duty cycle limits |
| Intake Fan | PWM/Relay | Variable speed | Temp-based curve |
| Exhaust Fan | PWM/Relay | Variable speed | Temp/humidity curve |
| Reservoir Refill | Solenoid/Relay | Timed open | Max refill duration, level confirm |

### 2.3 Automation Features
- **Scheduled feeding** — Multiple daily feeds, configurable times
- **Rule-based automation** — If/then rules (e.g., "if water_temp > 28°C then increase fan speed")
- **Water-level refill** — Automatic refill when level < threshold, with max duration safety
- **Ventilation curves** — Fan speed based on temperature/humidity curves
- **Circulation schedules** — Pump on/off cycles for water quality

### 2.4 Alert System
- **Threshold alerts** — Critical/warning levels for all sensors
- **Actuator fault alerts** — State mismatch, jam detection
- **System alerts** — Offline, simulator mode, calibration due
- **Cooldown periods** — Prevent alert spam (configurable, default 15 min)
- **Retention** — 30 days default

### 2.5 Remote Web Control (Admin)
- Real-time sensor dashboard
- Actuator manual control (with confirmation)
- Feeding schedule configuration
- Automation rule editor
- Alert history and acknowledgment
- System settings (thresholds, calibration, network)
- Emergency stop (all actuators off)

### 2.6 Local Touchscreen (Raspberry Pi)
- Same backend API as web UI
- Read-only monitoring mode (default)
- Admin unlock for local control
- Offline operation indicator
- Emergency stop hardware button (GPIO)

---

## 3. Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| **Availability** | 99.9% local operation; web UI requires network |
| **Latency** | Sensor readings < 500ms; actuator commands < 1s |
| **Data Retention** | Sensor readings: 1 year (partitioned); Alerts: 30 days |
| **Security** | JWT auth; HTTPS in production; rate limiting; CORS |
| **Scalability** | Single Pi 5; supports future multi-node |
| **Maintainability** | HAL enables sensor/actuator swap without app changes |
| **Testability** | Simulator mode for 100% software testing |

---

## 4. Hardware Architecture

### 4.1 Raspberry Pi 5 Responsibilities
- **Physical GPIO control** — All sensor reading, actuator driving
- **Hardware Abstraction Layer** — Runs HAL service/process
- **Local automation engine** — Runs independently of web backend
- **Local alert engine** — Evaluates thresholds locally
- **Touchscreen UI host** — Serves local display via kiosk browser
- **Data persistence** — Local SQLite buffer when offline; syncs to PostgreSQL
- **Time synchronization** — NTP when online; RTC when offline
- **Watchdog** — Hardware watchdog for system health

### 4.2 Sensor Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Hardware Abstraction Layer               │
├─────────────────────────────────────────────────────────────┤
│  SensorInterface (abstract base class)                      │
│  ├── read() → SensorReading                                 │
│  ├── calibrate(offset) → bool                               │
│  ├── health_check() → SensorHealth                          │
│  └── get_metadata() → SensorMetadata                        │
├─────────────────────────────────────────────────────────────┤
│  Implementations:                                           │
│  ├── PHSensor           (I2C/ADC)          → SimulatedPH    │
│  ├── WaterTempSensor    (1-Wire/DS18B20)    → SimulatedTemp │
│  ├── TDSSensor          (I2C/ADC)          → SimulatedTDS   │
│  ├── WaterLevelSensor   (Ultrasonic/GPIO)   → SimulatedLevel│
│  ├── AirTempSensor      (I2C/DHT22)        → SimulatedAir   │
│  └── HumiditySensor     (I2C/DHT22)        → SimulatedHumid │
└─────────────────────────────────────────────────────────────┘
```

**Key Principle:** All sensor implementations conform to `SensorInterface`. Application code depends only on the interface. Simulator implementations provide realistic data for development.

### 4.3 Actuator Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Hardware Abstraction Layer               │
├─────────────────────────────────────────────────────────────┤
│  ActuatorInterface (abstract base class)                    │
│  ├── activate(params) → ActuatorResult                      │
│  ├── deactivate() → ActuatorResult                          │
│  ├── get_state() → ActuatorState                            │
│  ├── calibrate() → CalibrationData                          │
│  └── health_check() → ActuatorHealth                        │
├─────────────────────────────────────────────────────────────┤
│  Implementations:                                           │
│  ├── FishFeeder         (Servo/Stepper/GPIO) → SimulatedFeed│
│  ├── WaterPump          (Relay/GPIO)        → SimulatedPump │
│  ├── OxygenPump         (Relay/GPIO)        → SimulatedPump │
│  ├── IntakeFan          (PWM/GPIO)          → SimulatedFan  │
│  ├── ExhaustFan         (PWM/GPIO)          → SimulatedFan  │
│  └── ReservoirRefill    (Solenoid/Relay)    → SimulatedValve│
└─────────────────────────────────────────────────────────────┘
```

**Key Principle:** All actuator implementations conform to `ActuatorInterface`. Application code depends only on the interface. Simulator implementations track virtual state.

### 4.4 GPIO Pin Mapping (BCM Numbering)

| Function | GPIO Pin | Interface | Notes |
|----------|----------|-----------|-------|
| pH Sensor | 4 | I2C/ADC | Atlas Scientific EZO |
| Water Temp | 17 | 1-Wire | DS18B20 |
| TDS Sensor | 27 | I2C/ADC | Gravity TDS |
| Water Level | 22 | GPIO | Ultrasonic HC-SR04 |
| Air Temp | 23 | I2C | DHT22 / SHT30 |
| Humidity | 24 | I2C | DHT22 / SHT30 |
| Fish Feeder | 18 | PWM | Servo/Stepper driver |
| Water Pump | 19 | GPIO | Relay module |
| Oxygen Pump | 20 | GPIO | Relay module |
| Intake Fan | 21 | PWM | 4-pin PWM fan |
| Exhaust Fan | 25 | PWM | 4-pin PWM fan |
| Reservoir Refill | 26 | GPIO | Solenoid valve relay |

### 4.5 I2C Addresses
| Device | Address | Bus |
|--------|---------|-----|
| pH Sensor (Atlas EZO) | 0x63 | 1 |
| TDS Sensor (Gravity) | 0x48 | 1 |
| Air Temp/Humidity (SHT30) | 0x44 | 1 |

---

## 5. Hardware Abstraction Strategy

### 5.1 Design Principles
1. **Interface Segregation** — Separate interfaces for sensors vs actuators
2. **Dependency Inversion** — Application depends on abstractions, not implementations
3. **Factory Pattern** — `HardwareFactory` creates appropriate implementation based on `HARDWARE_MODE`
4. **Configuration-Driven** — Pin mappings, I2C addresses, calibration in `.env`
5. **Hot-Swappable** — Change sensor/actuator without code changes (config only)

### 5.2 Hardware Modes
| Mode | Description | Use Case |
|------|-------------|----------|
| `simulator` | Pure software simulation | Development, CI, testing |
| `hardware` | Real GPIO/I2C/1-Wire on Pi 5 | Production, integration testing |
| `hybrid` | Mix of real + simulated | Partial hardware bring-up |

### 5.3 Simulator Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                      Simulator Core                         │
├─────────────────────────────────────────────────────────────┤
│  - Virtual sensor state (with noise, drift, trends)        │
│  - Virtual actuator state (with delays, failures)          │
│  - Scenario engine (preset scenarios: normal, stress, fail)│
│  - Time acceleration (for long-term testing)               │
│  - Deterministic seed for reproducible tests               │
├─────────────────────────────────────────────────────────────┤
│  SimulatedSensorReading:                                    │
│  - value: float (within realistic range)                   │
│  - timestamp: datetime                                      │
│  - quality: GOOD/DEGRADED/FAIL                             │
│  - metadata: {noise, drift, calibration_offset}            │
├─────────────────────────────────────────────────────────────┤
│  SimulatedActuatorState:                                    │
│  - state: ON/OFF/ERROR                                      │
│  - last_command: datetime                                   │
│  - position: float (for variable actuators)                │
│  - fault: None/JAM/OVERHEAT/DISCONNECTED                   │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 Sensor Replacement Procedure
1. Implement new `SensorInterface` subclass
2. Add pin/I2C config to `.env.example`
3. Register in `HardwareFactory`
4. Update simulator with equivalent behavior
5. No application logic changes required

---

## 6. Web Application Architecture

### 6.1 Frontend (React + TypeScript + Vite)

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── common/       # Buttons, inputs, modals, tables
│   │   ├── sensors/      # Sensor cards, charts, status
│   │   ├── actuators/    # Actuator controls, sliders, toggles
│   │   └── alerts/       # Alert list, banner, toast
│   ├── pages/            # Route-level pages
│   │   ├── Dashboard.tsx
│   │   ├── Sensors.tsx
│   │   ├── Actuators.tsx
│   │   ├── Feeding.tsx
│   │   ├── Automation.tsx
│   │   ├── Alerts.tsx
│   │   └── Settings.tsx
│   ├── hooks/            # Custom React hooks
│   │   ├── useWebSocket.ts
│   │   ├── useAuth.ts
│   │   ├── useSensors.ts
│   │   └── useActuators.ts
│   ├── services/         # API clients
│   │   ├── api.ts        # REST client (axios/fetch)
│   │   └── websocket.ts  # WS client with reconnection
│   ├── store/            # State management (Zustand/Redux)
│   ├── types/            # TypeScript interfaces
│   ├── utils/            # Helpers, formatters
│   └── styles/           # CSS/Tailwind
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 6.2 Backend (FastAPI)

```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── sensors.py
│   │   │   │   ├── actuators.py
│   │   │   │   ├── feeding.py
│   │   │   │   ├── automation.py
│   │   │   │   ├── alerts.py
│   │   │   │   ├── auth.py
│   │   │   │   └── system.py
│   │   │   └── router.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py         # Pydantic Settings
│   │   ├── security.py       # JWT, password hashing
│   │   ├── exceptions.py     # Custom exceptions
│   │   └── logging.py        # Structured logging
│   ├── db/
│   │   ├── session.py        # Async session management
│   │   ├── base.py           # Declarative base
│   │   └── init_db.py        # Migration runner
│   ├── models/               # SQLAlchemy models
│   │   ├── sensor_reading.py
│   │   ├── actuator_state.py
│   │   ├── feeding_schedule.py
│   │   ├── automation_rule.py
│   │   ├── alert.py
│   │   └── user.py
│   ├── repositories/         # Data access layer
│   │   ├── sensor_repo.py
│   │   ├── actuator_repo.py
│   │   ├── feeding_repo.py
│   │   ├── automation_repo.py
│   │   └── alert_repo.py
│   ├── services/             # Business logic
│   │   ├── sensor_service.py
│   │   ├── actuator_service.py
│   │   ├── feeding_service.py
│   │   ├── automation_service.py
│   │   ├── alert_service.py
│   │   └── hardware_service.py  # HAL integration
│   ├── schemas/              # Pydantic request/response
│   ├── websocket/
│   │   ├── manager.py        # Connection manager
│   │   ├── handlers.py       # Message handlers
│   │   └── auth.py           # WS token auth
│   └── main.py               # FastAPI app factory
├── tests/
├── alembic/
├── requirements.txt
├── pyproject.toml
└── Dockerfile
```

---

## 7. Database Architecture (PostgreSQL 18)

### 7.1 Schema Overview

```sql
-- Core tables
users (id, email, password_hash, role, created_at, updated_at, deleted_at)
sensor_readings (id, sensor_type, value, unit, quality, timestamp, metadata)
actuator_states (id, actuator_type, state, position, timestamp, metadata)
feeding_schedules (id, name, times, amount_grams, enabled, calibration_data, created_at, updated_at)
automation_rules (id, name, trigger_type, trigger_config, action_type, action_config, enabled, priority, created_at, updated_at)
alerts (id, alert_type, severity, message, sensor_type, threshold_value, actual_value, acknowledged, acknowledged_by, acknowledged_at, created_at, resolved_at)
system_settings (key, value, description, updated_at)
calibration_data (id, sensor_type, offset, factor, calibrated_at, calibrated_by)
```

### 7.2 Key Design Decisions
- **Partitioned sensor_readings** — Monthly partitions for time-series performance
- **Soft deletes** — `deleted_at` on all entity tables
- **Audit fields** — `created_at`, `updated_at` on all tables
- **Indexes** — FK columns, timestamp columns, composite for common queries
- **Enums** — PostgreSQL enums for sensor_type, actuator_type, alert_severity

### 7.3 Migrations
- **Alembic only** — Never direct schema changes
- **Naming** — `YYYYMMDD_HHMM_description.py`
- **Rollback** — Every migration must have downgrade()

---

## 8. API Architecture

### 8.1 REST Endpoints (v1)

| Resource | Endpoints |
|----------|-----------|
| **Sensors** | `GET /sensors` — List latest readings<br>`GET /sensors/{type}` — Single sensor detail<br>`GET /sensors/{type}/history` — Time-range history<br>`POST /sensors/{type}/calibrate` — Calibrate |
| **Actuators** | `GET /actuators` — List all states<br>`GET /actuators/{type}` — Single actuator state<br>`POST /actuators/{type}/activate` — Activate with params<br>`POST /actuators/{type}/deactivate` — Deactivate<br>`POST /actuators/{type}/calibrate` — Calibrate |
| **Feeding** | `GET /feeding/schedules` — List schedules<br>`POST /feeding/schedules` — Create schedule<br>`PUT /feeding/schedules/{id}` — Update schedule<br>`DELETE /feeding/schedules/{id}` — Delete<br>`POST /feeding/trigger` — Manual feed |
| **Automation** | `GET /automation/rules` — List rules<br>`POST /automation/rules` — Create rule<br>`PUT /automation/rules/{id}` — Update rule<br>`DELETE /automation/rules/{id}` — Delete |
| **Alerts** | `GET /alerts` — List (with filters)<br>`POST /alerts/{id}/acknowledge` — Acknowledge<br>`GET /alerts/stats` — Summary counts |
| **Auth** | `POST /auth/login` — Login → tokens<br>`POST /auth/refresh` — Refresh access token<br>`POST /auth/logout` — Revoke refresh token |
| **System** | `GET /system/status` — Health, mode, version<br>`POST /system/emergency-stop` — Disable all actuators<br>`GET /system/settings` — All settings<br>`PUT /system/settings` — Update settings |

### 8.2 WebSocket Protocol

**Endpoint:** `WS /ws?token=<access_token>`

**Message Format:**
```json
{
  "type": "sensor_update | actuator_state | alert | system_status | ack",
  "payload": {},
  "timestamp": "ISO8601",
  "request_id": "uuid"
}
```

**Client → Server:**
- `subscribe` — Subscribe to topics
- `unsubscribe` — Unsubscribe
- `actuator_command` — Control actuator (auth required)
- `ping` — Heartbeat

**Server → Client:**
- `sensor_update` — Real-time readings
- `actuator_state` — State changes
- `alert` — New alert
- `system_status` — Mode changes, errors
- `pong` — Heartbeat response

---

## 9. Real-Time Communication Strategy

- **WebSocket** for live sensor data, actuator states, alerts
- **REST** for configuration, history, commands
- **Connection Manager** — Tracks connections per user, handles broadcast
- **Heartbeat** — 30s ping/pong; disconnect on 3 missed
- **Reconnection** — Client: exponential backoff (1s, 2s, 4s, 8s, max 30s)
- **Message Batching** — Batch sensor updates at 1Hz to reduce traffic

---

## 10. Authentication & Authorization

### 10.1 JWT Tokens
- **Access Token** — 30 min, HS256, claims: `sub`, `role`, `exp`, `iat`, `jti`
- **Refresh Token** — 7 days, stored hashed in DB, rotated on use
- **Storage** — HttpOnly Secure cookies (web); Authorization header (API)

### 10.2 Roles (Thesis Prototype)
| Role | Permissions |
|------|-------------|
| `admin` | Full access: monitoring, control, config, admin |

### 10.3 Protected Endpoints
- All `/api/v1/*` require valid access token
- Actuator commands: additional rate limiting (10/min per user)
- Emergency stop: requires re-authentication (password confirmation)

---

## 11. Remote Control Workflow

```
User (Web UI)
    │
    ▼
POST /api/v1/actuators/fish_feeder/activate {duration: 2.5}
    │
    ▼
FastAPI: Validate JWT → Check rate limit → Validate params
    │
    ▼
ActuatorService.execute_command(actuator_type, command, params)
    │
    ▼
HardwareService.send_command(actuator_type, command, params)
    │
    ▼
HAL (HardwareFactory.get_actuator()).activate(params)
    │
    ▼
[Simulator] Update virtual state → Return result
[Hardware]  GPIO/PWM/I2C command → Read back state → Return result
    │
    ▼
ActuatorService: Persist ActuatorState → Broadcast WS event
    │
    ▼
Response: {success: true, actuator_state: {...}}
```

**Safety Checks:**
- Authentication required
- Rate limiting (per-user, per-actuator)
- Parameter validation (duration limits, position ranges)
- State confirmation (read back after command)
- Emergency stop overrides all

---

## 12. Automatic Feeding Workflow

### 12.1 Feeding Calculation
```
Daily Feed (grams) = Fish Population × Avg Fish Weight (g) × Feeding % / 100
Per Feed Amount = Daily Feed / Feeding Frequency
Feeder Duration = Per Feed Amount / Feeder Dispense Rate (g/s)
```

### 12.2 Calibration Procedure
1. **Dispense Test** — Run feeder for N seconds, weigh output
2. **Calculate Rate** — grams/second = weight / seconds
3. **Repeat** — 3 runs (configurable), use median
4. **Store** — Save to `calibration_data` and `.env`

### 12.3 Feeding Schedule Execution
```
Scheduler (cron-like) checks every minute:
    For each enabled schedule:
        If current time matches schedule time:
            Calculate amount from calibration + population config
            Validate: amount ≤ max_per_feed (safety)
            Activate feeder for calculated duration
            Record: FeedingEvent(schedule_id, amount, duration, timestamp)
            Broadcast: WS feeding_complete event
```

### 12.4 Safety Limits
- Max feed per day: 5% of total biomass
- Max single feed duration: 30 seconds
- Cooldown between feeds: 30 minutes minimum
- Population changes require re-calculation

---

## 13. Water-Level / Refill Workflow

### 13.1 Monitoring
- **Interval:** Every 30 seconds (configurable)
- **Sensor:** Ultrasonic distance → percentage calculation
- **Smoothing:** Moving average (5 readings)

### 13.2 Thresholds & Actions
| Level | Threshold | Action |
|-------|-----------|--------|
| Critical Low | < 15% | **Immediate refill** + Critical alert |
| Warning Low | < 25% | **Scheduled refill** + Warning alert |
| Optimal | 40–80% | No action |
| Critical High | > 95% | Alert only (overflow risk) |

### 13.3 Refill Procedure
```
Refill Triggered:
    1. Check: Refill not already active
    2. Check: Reservoir has water (reservoir_level_sensor)
    3. Activate: ReservoirRefill valve (solenoid)
    4. Monitor: Water level every 5s
    5. Stop when: Level ≥ Optimal Min (40%) OR Max Duration (5 min)
    6. Deactivate: Valve
    7. Record: RefillEvent(duration, start_level, end_level, trigger)
    8. Alert: Refill complete / timeout / reservoir empty
```

### 13.4 Safety
- **Max refill duration:** 5 minutes (configurable)
- **Reservoir level check:** Prevent dry-run
- **Cooldown:** 30 min between auto-refills
- **Manual override:** Admin can trigger/cancel via UI

---

## 14. Alert Workflow

### 14.1 Alert Generation
```
Sensor Reading Received
    │
    ▼
AlertService.evaluate(reading)
    │
    ├── Check: value vs critical thresholds → CRITICAL alert
    ├── Check: value vs warning thresholds → WARNING alert
    ├── Check: actuator state mismatch → FAULT alert
    └── Check: system health (offline, sim mode) → INFO alert
    │
    ▼
If alert condition met AND cooldown expired:
    Create Alert record
    Broadcast WS alert event
    If email enabled: Queue email notification
```

### 14.2 Alert Lifecycle
`ACTIVE` → `ACKNOWLEDGED` → `RESOLVED` (auto when condition clears)

### 14.3 Cooldown
- Per alert type + sensor/actuator: 15 min default
- Configurable per threshold

---

## 15. Local Touchscreen Architecture

### 15.1 Deployment
- **Kiosk Mode Browser** (Chromium/Firefox) on Pi 5
- **URL:** `http://localhost:3000` (frontend dev server) or `http://localhost:8000` (served by backend)
- **Auto-start:** systemd service + `.xinitrc` / Wayland kiosk

### 15.2 Features
- **Read-Only Dashboard** — Default view, no auth required
- **Admin Unlock** — PIN/password for local control
- **Offline Indicator** — Visual badge when backend unreachable
- **Emergency Stop Button** — Large hardware button (GPIO) + on-screen
- **Local Automation Status** — Shows if local engine is running

### 15.3 Offline Behavior
- Frontend caches last known sensor data
- Local automation engine continues (runs on Pi independently)
- Touchscreen shows "Offline Mode" banner
- Commands queue locally, sync when online

---

## 16. Hardware Simulator Architecture

### 16.1 Simulator Modes
| Mode | Behavior |
|------|----------|
| `normal` | Realistic values with noise, gradual trends |
| `stress` | Values near thresholds, frequent fluctuations |
| `failure` | Sensor disconnects, actuator jams, comm errors |
| `calibration` | Known fixed values for calibration testing |

### 16.2 Sensor Simulation Models
```
pH:          Random walk 6.5–7.5, noise ±0.1, drift ±0.01/day
Water Temp:  Diurnal cycle 22–26°C, noise ±0.2°C
TDS:         Slow drift 400–800, noise ±10, spikes on feeding
Water Level: Slow decline 1%/hour (evaporation), step up on refill
Air Temp:    Diurnal 20–28°C, correlates with water temp
Humidity:    Inverse to temp, 50–70%, noise ±2%
```

### 16.3 Actuator Simulation Models
```
Feeder:      Activates → runs for duration → dispenses grams = rate × duration
Pumps:       On/Off with 100ms delay, 1% chance of "jam" fault
Fans:        PWM 0–100%, responds in 200ms, thermal protection at 100% > 10min
Refill:      Valve open → level rises 5%/sec → auto-close at target or timeout
```

### 16.4 Scenario Engine
- **Preset Scenarios** — YAML files defining sensor/actuator behavior over time
- **Time Acceleration** — 1x, 10x, 60x, 3600x for long-term testing
- **Deterministic Seed** — Reproducible test runs

---

## 17. Offline / Local Operation Strategy

### 17.1 Raspberry Pi Autonomy
The Pi 5 runs **two independent processes**:
1. **HAL + Local Automation + Local Alerts** — Always running, no network needed
2. **FastAPI Backend** — Serves web UI, syncs data, requires network for remote access

### 17.2 Data Sync Strategy
```
Local (Pi)                          Remote (PostgreSQL)
┌─────────────────┐                 ┌─────────────────┐
│ SQLite Buffer   │ ───sync──────▶  │ PostgreSQL      │
│ (sensor data,   │  (when online)  │ (persistent,    │
│  actuator logs, │                 │  partitioned)   │
│  alerts)        │                 │                 │
└─────────────────┘                 └─────────────────┘
       │                                    │
       ▼                                    ▼
Local Automation                      Web UI / Analytics
Engine runs                           reads from PG
```

### 17.3 Conflict Resolution
- **Last-write-wins** for settings (timestamp-based)
- **Append-only** for sensor readings (no conflicts)
- **Actuator commands** — Local takes precedence; remote commands queued

### 17.4 Offline Detection
- Backend health check every 30s
- Frontend shows connection status
- Local engine logs "offline mode" to systemd journal

---

## 18. AI / Analytics Boundary

### 18.1 Permitted AI Functions
- **Trend Analysis** — "pH declining 0.1/week"
- **Anomaly Detection** — "Water temp spike unusual for time of day"
- **Recommendations** — "Consider increasing feeding by 10%"
- **Predictive Maintenance** — "Feeder calibration drift detected"
- **Optimization** — "Fan curve could save 15% energy"

### 18.2 Prohibited AI Functions
- ❌ Direct actuator commands
- ❌ Override safety thresholds
- ❌ Disable emergency stop
- ❌ Modify automation rules without admin approval
- ❌ Calibrate sensors without human verification

### 18.3 Implementation Pattern
```
AI Service → Generates Recommendation → Admin Review → Admin Approves → Applied via API
     │                                           │
     └── Audit Log: All recommendations logged with confidence scores
```

---

## 19. Security Requirements

### 19.1 Network
- **Production:** HTTPS only (TLS 1.3), HSTS
- **CORS:** Frontend origin only
- **Rate Limiting:** 100 req/min per IP; 10 actuator/min per user

### 19.2 Authentication
- bcrypt (12+ rounds) for passwords
- JWT HS256, short access + rotating refresh
- Secure HttpOnly cookies (SameSite=Strict)
- Token revocation on logout/password change

### 19.3 Hardware
- Emergency stop: dedicated GPIO, hardware interrupt
- Actuator rate limits enforced in HAL
- State validation before every command
- No unauthenticated actuator endpoints

### 19.4 Secrets
- `.env` never committed
- `.env.example` with placeholders only
- Database password: 32+ chars, rotated quarterly
- JWT secret: 64+ chars, rotated on compromise

---

## 20. Testing Strategy

### 20.1 Test Pyramid
```
                    ┌─────────────┐
                    │   E2E       │  ← Playwright: Critical flows
                    │  (10%)      │     Login, Feeding, E-Stop
            ┌───────┤             │
            │       └─────────────┘
            │       ┌─────────────┐
            │       │ Integration │  ← pytest/Vitest: API, HAL, DB
            │       │  (30%)      │     Sensor→DB, Actuator→HAL
    ┌───────┤       └─────────────┘
    │       │       ┌─────────────┐
    │       │       │   Unit      │  ← pytest/Vitest: Pure logic
    │       │       │  (60%)      │     Calculations, Validation
    └───────┤       └─────────────┘
            │
            └─────── Hardware Simulator Tests
                    ┌─────────────┐
                    │  Simulator  │  ← Validate ranges, transitions
                    │ Validation  │     Failure modes, Calibration
                    └─────────────┘
```

### 20.2 Coverage Targets
| Layer | Target |
|-------|--------|
| Backend Unit + Integration | ≥ 80% |
| Frontend Component + Integration | ≥ 70% |
| E2E Critical Flows | 100% |

### 20.3 Hardware Simulator Tests
- Sensor output ranges match specs
- Actuator state transitions correct
- Failure injection (disconnect, jam, timeout)
- Calibration procedure validation
- Time acceleration accuracy

---

## 21. Development Phases

### Phase 1: Foundation (Current)
- [x] Project structure, docs, config
- [ ] Database models & migrations
- [ ] HAL interfaces + simulator implementations
- [ ] FastAPI skeleton with config, security, logging
- [ ] React + TS + Vite scaffold with routing, auth context

### Phase 2: Core Backend
- [ ] Sensor ingestion (REST + WS broadcast)
- [ ] Actuator control endpoints + HAL integration
- [ ] Automation engine (scheduler + rule evaluator)
- [ ] Alert engine (threshold eval + cooldown + WS)
- [ ] JWT auth (login, refresh, logout, middleware)
- [ ] Feeding service (calculation, scheduling, calibration)
- [ ] Refill service (monitoring, trigger, safety)

### Phase 3: Frontend Application
- [ ] Real-time dashboard (sensor cards, charts)
- [ ] Actuator control panel (with confirmations)
- [ ] Feeding schedule UI (CRUD + calibration wizard)
- [ ] Automation rule builder (visual)
- [ ] Alert center (list, ack, history)
- [ ] Settings pages (thresholds, calibration, network)

### Phase 4: Integration & Testing
- [ ] Simulator validation suite
- [ ] E2E test scenarios
- [ ] Offline mode verification
- [ ] Pi 5 deployment scripts (systemd, kiosk, nginx)

### Phase 5: Hardware Integration (Future)
- [ ] GPIO/I2C/1-Wire driver implementations
- [ ] Physical sensor calibration
- [ ] Actuator tuning (PWM curves, relay timing)
- [ ] Field testing & documentation

---

## 22. Future Hardware Replacement Strategy

### 22.1 Sensor Replacement
```python
# 1. New sensor class implements SensorInterface
class NewPHSensor(SensorInterface):
    def read(self) -> SensorReading: ...
    def calibrate(self, offset: float) -> bool: ...

# 2. Register in factory
HardwareFactory.register_sensor("ph", NewPHSensor, config_key="PH_SENSOR")

# 3. Add simulator equivalent
class SimulatedNewPH(SimulatedSensor): ...

# 4. Update .env.example with new pin/I2C config
# 5. Deploy — zero application code changes
```

### 22.2 Actuator Replacement
```python
# 1. New actuator class implements ActuatorInterface
class NewFeeder(ActuatorInterface):
    def activate(self, params): ...
    def calibrate(self): ...

# 2. Register in factory
HardwareFactory.register_actuator("fish_feeder", NewFeeder, config_key="FEEDER")

# 3. Add simulator equivalent
# 4. Update .env.example
# 5. Deploy — zero application code changes
```

### 22.3 Platform Migration (Pi 5 → Future)
- HAL isolates platform-specific code
- Factory pattern enables new platform backends
- Simulator remains unchanged
- Only `HardwareFactory` and driver implementations change

---

## 23. Configuration Reference

All runtime configuration via environment variables (see `.env.example`):

| Category | Variables |
|----------|-----------|
| App | `APP_NAME`, `APP_ENV`, `DEBUG`, `SECRET_KEY`, `API_PREFIX` |
| Database | `DATABASE_URL`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` |
| Auth | `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` |
| Hardware | `HARDWARE_MODE`, `RASPBERRY_PI_HOST`, `RASPBERRY_PI_PORT`, `GPIO_*`, `*_I2C_ADDR` |
| Calibration | `*_CALIBRATION_*` |
| Feeding | `FEEDER_*`, `DEFAULT_FISH_*`, `FEEDING_*` |
| Water Level | `WATER_LEVEL_*` |
| Thresholds | `PH_*`, `WATER_TEMP_*`, `AIR_TEMP_*`, `HUMIDITY_*`, `TDS_*` |
| Timing | `*_INTERVAL_*` |
| Alerts | `ALERT_*`, `SMTP_*` |
| WebSocket | `WS_*` |
| Frontend | `VITE_API_URL`, `VITE_WS_URL`, `VITE_APP_TITLE` |

---

## 24. Appendix: Data Flow Summary

```
┌─────────────┐    Sensor Reading     ┌─────────────┐
│  Sensors    │ ────────────────────▶ │     HAL     │
│  (Physical  │                       │  (Interface │
│   or Sim)   │                       │   + Impl)   │
└─────────────┘                       └──────┬──────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ HardwareService │
                                    │ (Business Logic)│
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    ▼                        ▼                        ▼
            ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
            │  Database   │         │Automation   │         │   Alert     │
            │ (PostgreSQL)│         │  Engine     │         │   Engine    │
            └─────────────┘         └─────────────┘         └─────────────┘
                    │                        │                        │
                    ▼                        ▼                        ▼
            ┌─────────────────────────────────────────────────────────────┐
            │                    FastAPI Backend                          │
            │  REST API ◀──────────────────────────────────────▶ WebSocket│
            └────────────────────────────┬────────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
            │  Web UI     │      │  Touchscreen│      │   Mobile    │
            │  (React)    │      │  (Kiosk)    │      │   (Future)  │
            └─────────────┘      └─────────────┘      └─────────────┘
```

---

*End of SYSTEM_BLUEPRINT.md*