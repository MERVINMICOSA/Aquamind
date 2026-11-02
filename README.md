# AquaMind

**Smart Aquaponics Monitoring and Automation System**

A thesis prototype for an intelligent aquaponics management system built on Raspberry Pi 5 with a React/TypeScript frontend and FastAPI backend.

---

## 📋 Project Overview

AquaMind provides comprehensive monitoring and automated control for aquaponics systems, tracking critical water quality parameters and environmental conditions while managing actuators for feeding, circulation, aeration, ventilation, and water level maintenance.

### Monitored Parameters
- **Water Quality**: pH, Temperature, TDS (Total Dissolved Solids), Water Level
- **Environment**: Air Temperature, Humidity

### Controlled Actuators
- Automatic Fish Feeder
- Water Circulation Pump
- Oxygen/Aeration Pump
- Intake Fan
- Exhaust Fan
- Reservoir Refill Mechanism

---

## 🏗️ Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  Admin Browser  │────▶│  React + TS      │────▶│  FastAPI Backend   │
│  (Web UI)       │     │  (Frontend)      │     │  (REST + WebSocket)│
└─────────────────┘     └──────────────────┘     └─────────┬──────────┘
                                                           │
                    ┌──────────────────────────────────────┼──────────┐
                    ▼                                      ▼          ▼
            ┌───────────────┐                    ┌───────────────┐ ┌─────────┐
            │  PostgreSQL   │                    │  Automation   │ │ Alert   │
            │  18 Database  │                    │  Engine       │ │ Engine  │
            └───────────────┘                    └───────────────┘ └─────────┘
                                                           │
                                                           ▼
                                              ┌─────────────────────────┐
                                              │ Hardware Abstraction    │
                                              │ Layer (HAL)             │
                                              └───────────┬─────────────┘
                                                          │
                    ┌─────────────────────────────────────┼─────────────┐
                    ▼                                     ▼             ▼
            ┌───────────────┐                    ┌───────────────┐ ┌─────────┐
            │   Sensors     │                    │  Actuators    │ │Simulator│
            │ (pH, Temp,    │                    │ (Feeder,      │ │(Dev)    │
            │  TDS, Level,  │                    │  Pumps, Fans, │ │         │
            │  Air T/H)     │                    │  Refill)      │ │         │
            └───────────────┘                    └───────────────┘ └─────────┘
```

### Local Touchscreen
The Raspberry Pi 5 hosts a local touchscreen interface that communicates with the same backend API, providing on-site monitoring and control without requiring network connectivity.

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Hardware Controller** | Raspberry Pi 5 |
| **Backend Framework** | FastAPI (Python 3.11+) |
| **Frontend Framework** | React 18 + TypeScript |
| **Build Tool** | Vite |
| **Database** | PostgreSQL 18 |
| **Real-time** | WebSocket (FastAPI native) |
| **Authentication** | JWT (Admin-only role) |
| **Hardware Abstraction** | Custom HAL with simulator mode |
| **Testing** | pytest, Vitest, Playwright |

---

## 🚀 Development Roadmap

### Phase 1: Foundation (Current)
- [x] Project structure & documentation
- [ ] Database schema & models
- [ ] Hardware abstraction layer with simulator
- [ ] Basic FastAPI application skeleton
- [ ] React + TypeScript + Vite frontend scaffold

### Phase 2: Core Backend
- [ ] Sensor data ingestion & storage
- [ ] Actuator control endpoints
- [ ] Automation engine (schedules, rules)
- [ ] Alert engine (thresholds, notifications)
- [ ] WebSocket real-time updates
- [ ] JWT authentication (admin role)

### Phase 3: Frontend Application
- [ ] Dashboard with real-time sensor display
- [ ] Historical data visualization
- [ ] Actuator control panel (admin)
- [ ] Feeding schedule configuration
- [ ] Alert management UI
- [ ] System settings & calibration

### Phase 4: Integration & Testing
- [ ] Hardware simulator validation
- [ ] End-to-end testing
- [ ] Offline/local operation verification
- [ ] Raspberry Pi 5 deployment preparation

### Phase 5: Hardware Integration (Future)
- [ ] Physical sensor/actuator integration
- [ ] GPIO driver implementation
- [ ] I2C/SPI sensor drivers
- [ ] Field testing & calibration

---

## 📍 Current Phase

**Phase 1: Foundation** — Establishing project documentation, directory structure, and development environment.

> **Note**: Physical hardware integration will happen **after** the complete software prototype is working with the hardware simulator. The simulator provides realistic sensor data and actuator responses for development and testing.

---

## 🔐 Key Architectural Decisions (Confirmed)

| Decision | Status |
|----------|--------|
| ESP32 → Raspberry Pi 5 | ✅ Confirmed |
| Misting system → Removed | ✅ Confirmed |
| Interactive touchscreen → Added | ✅ Confirmed |
| Remote web controls → Added | ✅ Confirmed |
| Automatic calibrated feeding → Retained | ✅ Confirmed |
| Admin-only role → Confirmed | ✅ Confirmed |
| PostgreSQL 18 → Selected | ✅ Confirmed |
| AI/analytics → Advisory only (no safety-critical control) | ✅ Confirmed |

---

## 📁 Project Structure

```
aquamind/
├── backend/           # FastAPI application
├── frontend/          # React + TypeScript + Vite
├── hardware/          # Hardware abstraction layer & simulator
├── database/          # Migrations, seeds, schemas
├── tests/             # Test suites (unit, integration, e2e)
├── docs/              # Additional documentation
├── .gitignore
├── .env.example
├── README.md
├── CLAUDE.md
└── SYSTEM_BLUEPRINT.md
```

---

## 📚 Documentation

- **[SYSTEM_BLUEPRINT.md](SYSTEM_BLUEPRINT.md)** — Complete architecture specification
- **[CLAUDE.md](CLAUDE.md)** — Development guidelines for AI-assisted development
- **[.env.example](.env.example)** — Configuration template

---

## ⚠️ Safety Notes

- **No AI control of safety-critical hardware** — AI/analytics provide recommendations only
- **Hardware abstraction mandatory** — Frontend never accesses GPIO directly
- **Offline-capable** — Raspberry Pi operates autonomously without internet
- **Admin-only access** — Thesis prototype uses single admin role

---

## 📄 License

Thesis prototype — Academic use.