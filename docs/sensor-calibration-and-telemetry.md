# AquaMind sensor reading and calibration boundaries

## What is implemented

1. ESP32 packets transmitted over the Pi's USB serial port are validated and stored in the **ESP32 telemetry archive**.
2. Registered AquaMind `sensors` have their own **sensor_readings** history and separate **sensor_calibrations** records. A saved ESP32 packet **does not automatically create** a registered reading, update the sensor's calibration status, or trigger a threshold alert.
3. Sensor Detail now shows read-only saved calibration history and distinguishes that evidence from the registered sensor's `calibration_status`.
4. Sensor-triggered **threshold alerts and actuator automation** skip pH and TDS sensor records unless the registered sensor is marked `verified`. Disabled or deleted sensors do not generate threshold alerts. This prevents obvious unverified readings from driving alerts or actions but **does not physically prove a probe was calibrated**.
5. The Water Flow website work is separate: external pumps remain independent of AquaMind, while the ESP32 servo fish feeder remains a planned controlled subsystem.

## Calibration checklist

- Verify sensor wiring and raw acquisition before calibrating.
- For pH, measure at known reference buffers and the relevant temperature (for example 4.01, 6.86, 9.18 when available and suitable). Keep both actual reference and device output.
- For TDS/EC, use a known reference solution and the probe's supported temperature-compensation procedure.
- Calculate/apply the ESP32 firmware calibration **on the device**, test it against reference points, and save the corresponding record to AquaMind after a real verification.
- Review recorded timestamps, reading quality, units, and source. Stored calibration metadata, a `verified` flag, and ESP32's own `ph_calibrated` or `tds_calibrated` flag must not be treated as independent measurement proof.
- Only then consider enabling normal threshold alerts for calibrated sensor data. Keep raw voltages and `*_unverified_*` packet values diagnostic-only.

## Gap before automatic ESP32-to-sensor ingestion

A deliberate ingestion design is required rather than blindly copying packet values into registered sensor readings:

- Pair the exact `device_id` and registered sensor identity, with a configured map of packet fields to sensor IDs, measurement types, and units.
- Include deduplication and timestamp/sequence reconciliation across ESP32 reboots and USB reconnects.
- Validate each field's presence, range, calibration/quality provenance, and read outcome; **never** map `ph_unverified_estimate` or `tds_unverified_ppm` into trusted pH/TDS readings.
- Reconcile the device-reported calibrated flag with registered sensor calibration status and approved calibration records; do not silently upgrade trust from a boolean sent by the microcontroller.
- Persist first, then only evaluate appropriate alerts; never activate the external pump and never infer flow from water-level values.
- Test invalid/missing calibration, device ID mismatch, duplicate packets, stale data, out-of-order data, and incomplete sensor readings before using this in unattended operation.

**No automatic bridge from the ESP32 packet archive to registered sensor readings is added by this PR.** That should be implemented separately with explicit identity mappings and integration tests.
