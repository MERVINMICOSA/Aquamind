# AquaMind: ESP32 servo feeder integration contract (planned)

## Scope

The water circulation pump is **externally powered and continuously running**. AquaMind does not control the circulation pump or its relays. The fish feeder is a **separate actuator**: an ESP32-driven servo with a mechanical food dispenser.

This document describes the intended feeder subsystem. **It is not implemented by merely configuring a feeding schedule.** At present, the Raspberry Pi ESP32 USB serial service receives sensor telemetry; it does not transmit feeder movement commands or process feeder acknowledgments.

## Existing reusable functionality

- `fish_feeder` actuator records and tank association
- feeding schedules and feeding event history
- feeder calibration (measured grams and measured seconds)
- fish population / biomass-based feeding calculations
- per-feed limits and runtime validation in feeding services

Keep these features when retiring water-pump relays. Never use a water_pump actuator as a feeding target.

## Hardware and wiring requirements

- ESP32 DevKit, servo matched to the dispenser's required torque, and a stable **external regulated servo supply** capable of the servo's startup/stall current
- PWM-compatible ESP32 output on a safe board pin (exact pin chosen after confirming the board and other sensor wiring)
- common **GND** between the ESP32 and the external servo supply
- signal lead to the servo control input, supply leads to the external regulated supply (not an ESP32 GPIO pin)
- protected wiring, mechanical stop/limits, splash protection, and a food-safe dispenser that cannot jam open
- manual, physically supervised commissioning before any unattended scheduled feeding

Do not power the servo from an ESP32 GPIO pin. Avoid selecting boot/strapping pins without checking the specific ESP32 model. A software command cannot prove physical food delivery.

## Planned host-to-device flow

1. A validated feeding schedule becomes due on the Raspberry Pi.
2. The backend calculates the feed amount using the recorded tank biomass and validated dispenser calibration.
3. Server-side checks apply a per-feed maximum, minimum interval/cooldown, bounded servo motion/runtime, and a stop-on-error policy.
4. The Raspberry Pi sends **one** bounded, identified feeder command to the specific ESP32 over the existing locally attached USB interface, using a dedicated command type separate from `aquamind_sensor` telemetry.
5. The ESP32 validates device/command identity and limits, deduplicates command IDs, moves the servo between calibrated positions, and reports a bounded acknowledgment or explicit fault.
6. AquaMind records the attempt and its verified **controller** result without claiming food delivery was physically measured.

### Protocol design work still needed

- versioned command and acknowledgment schemas; command UUID / monotonic deduplication
- serial reader/writer coordination to prevent competing access to the USB port
- explicit outcome states (requested, accepted, completed-by-controller, failed, timed-out) and a clear distinction from physically confirmed delivery
- startup state, retransmission policy (no automatic replay of non-idempotent feed movement), command timeout, and watchdog behavior
- ESP32 firmware servo controller and its collision-free integration with sensor telemetry
- Pi configuration, local-only command permissions, audit records, and tests using a simulated serial device before live use

## Safety and test gates

- **Do not enable unattended feeding before the hardware command path and acknowledgments are tested.**
- Limit feed grams and servo movement/cycles per request; enforce a minimum time between requests.
- Servo returns to a safe/rest position on reset and communication loss. Ensure the mechanism is spring-safe or mechanically unable to dump the whole hopper on failure.
- Test disconnects, Pi reboot, duplicate commands, corrupt packets, starvation of incoming telemetry, power failures, and servo stalls.
- Persisted schedules, simulated success, and controller acknowledgments must not be presented as confirmed dispensing without independent hardware feedback.

## Website behavior now

The Feeding page explains the planned ESP32 servo feeder and its prerequisites. It lists only fish_feeder actuator records for schedules/calibration and tells operators that the current USB link is receive-only. Water Flow remains an informational page and contains **no pump/relay controls**.
