# ESP32 USB packets → registered AquaMind sensor readings

## Status and safety

The existing USB receiver archives complete schema-v1 `aquamind_sensor`
packets in `esp32_telemetry` and exposes them on the dashboard.

This **opt-in bridge** additionally creates registered `sensor_readings` from
**explicitly mapped** packet fields and evaluates sensor threshold alerts.
It never issues actuator commands, controls the external circulation pump,
or operates the independent ESP32 servo feeder.

**Disabled by default.** Do not enable until mappings and real sensor hardware
are confirmed. Existing ESP32 packet archiving remains functional if the
bridge is disabled.

## Enablement

The Raspberry Pi systemd installer reads
`backend/deploy/aquamind-runtime.env` and
`backend/deploy/raspberry-pi5.hardware.env`. Configure the actual ESP32
device and system identifiers on the Pi, **not in GitHub**:

```ini
ESP32_SERIAL_ENABLED=true
ESP32_SERIAL_PORT=/dev/serial/by-id/YOUR_ACTUAL_ESP32_DEVICE
ESP32_SERIAL_BAUDRATE=115200
ESP32_DEVICE_ID=esp32-devkit-01
ESP32_SYSTEM_ID=YOUR_EXISTING_AQUAMIND_SYSTEM_UUID

# Enable only when all mappings and calibration prerequisites are ready.
ESP32_SENSOR_BRIDGE_ENABLED=false
ESP32_SENSOR_MAP_JSON='{"water_temp_c":"YOUR_REGISTERED_SENSOR_UUID","humidity_pct":"OTHER_REGISTERED_SENSOR_UUID"}'
```

Replace placeholder values with IDs from the actual AquaMind database.
Choose an existing `/dev/serial/by-id/...` device where possible to avoid
changes in `ttyUSB` / `ttyACM` numbering. The systemd env file may require
quoting the JSON as shown. Restart the service after changing the settings.

Once the sensor rows match and the test procedure below passes, change
`ESP32_SENSOR_BRIDGE_ENABLED=true` and restart the service. Keep
`HARDWARE_ENABLED=false` for the Raspberry Pi GPIO/relay subsystem.

### Registering sensors

Use authenticated `/api/v1/sensors` administration endpoints to create
one existing physical, enabled, **non-simulated** sensor record per field.
The `system_id` must match `ESP32_SYSTEM_ID` and the
`hardware_identifier` must exactly match the
`<ESP32_DEVICE_ID>:<field>` pattern. Example:

```json
{
  "system_id": "YOUR_EXISTING_AQUAMIND_SYSTEM_UUID",
  "name": "Fish tank water temperature",
  "sensor_type": "water_temperature",
  "measurement_type": "temperature",
  "location_type": "tank",
  "unit": "°C",
  "hardware_identifier": "esp32-devkit-01:water_temp_c",
  "is_simulated": false,
  "is_enabled": true,
  "sampling_interval_seconds": 30,
  "calibration_status": "pending"
}
```

The response contains the sensor UUID to place in `ESP32_SENSOR_MAP_JSON`.
Do not map every value to one sensor ID: **each field requires a distinct
registered sensor row**. Unknown fields, malformed UUIDs and duplicate mapped
sensor IDs fail startup validation rather than silently being accepted.

### Supported fields

| ESP32 field | Sensor type | Measurement type | Exact unit |
|---|---|---|---|
| `water_temp_c` | `water_temperature` | `temperature` | `°C` |
| `ph` | `ph` | `ph` | `pH` |
| `tds_ppm` | `tds` | `tds` | `ppm` |
| `water_level_pct` | `water_level` | `level` | `%` |
| `water_height_cm` | `water_level` | `level` | `cm` |
| `distance_cm` | `water_level` | `level` | `cm` |
| `air_temp_c` | `air_temperature` | `temperature` | `°C` |
| `humidity_pct` | `humidity` | `humidity` | `%` |

Fields with null values are skipped. If the packet explicitly reports
`raw_readings.<sensor>.status` other than `ok`, that field is skipped,
even if a top-level number was supplied. Raw voltages, unverified estimates
and wet/dry flags are **never promoted** to registered sensor measurements.

### pH and TDS calibration safety

The bridge will accept `ph` / `tds_ppm` **only** when all apply:

1. Schema-v1 packet carries a non-null calibrated value and its
   `ph_calibrated` / `tds_calibrated` flag is true.
2. The mapped physical sensor row has `calibration_status=verified`.
3. Its **most recent** calibration record is `status=verified`, includes
   `verified_by_user_id` (a real approving user), and its
   `calibration_data` includes
   `{"esp32_device_id": "esp32-devkit-01", "firmware_applied": true}`.

The metadata must be entered only after physically confirming reference
solutions and the currently installed ESP32 firmware. These checks do not
prove that the physical probe or ESP32 firmware is accurate. A future protocol
extension with a verified calibration revision/device signature could provide
stronger binding. Never mark a calibration `verified` just to make an alert
or dashboard reading appear.

If pH/TDS is missing or unverified, raw packet storage and other mapped
environmental readings continue; pH/TDS never become fake GOOD readings.

## Transaction and alert guarantees

- One accepted, previously unseen packet identity
  `(system_id, device_id, sequence, uptime_ms)` produces at most one set
  of mapped sensor readings.
- The packet, accepted mapped readings and threshold alerts commit as
  **one database transaction**. An exception rolls the transaction back
  (there is no partial packet-to-reading save).
- A byte-for-byte-equivalent retry is a duplicate and creates no readings
  or alerts. A conflicting packet using the same identity is rejected.
- Sensor timestamp is the Raspberry Pi's UTC **receipt time**, not an
  invented ESP32 wall clock timestamp. Device `sequence` is preserved on
  each registered reading.
- **Historical raw packets are not backfilled** into registered sensor
  histories by merely enabling the bridge. Only newly accepted packets
  are mapped.
- The existing calibration-gated threshold alerts are evaluated. No
  sensor-triggered automation or relay operation is executed by this
  bridge. A separate feeder-command system remains future work.

### Limits to know before field deployment

The v1 packet has `uptime_ms` and `sequence`, but no persistent boot ID
or absolute measurement timestamp. On a complete ESP32 reboot, identity
reuse may occur; such collisions are deliberately treated as duplicates
or conflicts rather than causing duplicate alerts. Buffered, out-of-order
packets cannot always be distinguished from genuinely new packets. For
stronger ordering across resets, add firmware `boot_id` and a device
timestamp in a separately versioned protocol, then migrate the archive
identity and tests.

## Commissioning checks

1. Confirm the ESP32 packet archive is updating in the dashboard first.
2. Register mapped sensors with exact units and hardware identifiers.
3. With bridge **off**, check each raw packet field and any read-fault
   diagnostics. Correct wiring and calibration first.
4. Enable the bridge for **water temperature only** and verify that a new
   packet creates one `sensor_readings` row, appears on Sensors, and
   updates the trend. Disconnect/reconnect USB and verify no duplicate
   rows for retried packets.
5. Add air temperature, humidity and optional water-level mappings
   one at a time. Verify all sensor locations, values, units and timing.
6. Only after actual pH/TDS buffer/reference testing and recorded
   physical calibration, configure their verified calibration records
   and mappings.
7. Configure suitable enabled alert thresholds and verify warning and
   critical test cases with synthetic fixtures **before** relying on live
   alerts. Confirm no actuator or circulation commands occur.
8. Confirm the frontend backend API URL is correct for the Pi deployment.
   Keep the website and USB serial service restricted to intended users.

## Development verification

Run:
```bash
cd backend
python -m pytest -q tests/test_esp32_sensor_bridge.py tests/test_esp32_serial_service.py
python -m pytest -q
```

No real ESP32 is connected during GitHub CI. Field calibration and end-to-end
USB tests on the Raspberry Pi remain necessary before unattended operation.
