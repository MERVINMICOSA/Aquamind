# AquaMind: automatic ESP32 sensor discovery

## What changes

The Sensors website shows **only current, usable readings** from the Raspberry
Pi's archived ESP32 USB packets. It does not expose device IDs, sensor UUIDs,
hardware identifiers, sequence numbers, or raw diagnostic tables in the ordinary
Sensors view. A sensor is marked **Active** only while the newest packet has been
received recently and that value is present, not explicitly failed, and usable.
If packets stop, old values are not displayed as active.

Registered sensor database history is optional and separate from the simplified
live monitoring display. The opt-in bridge **automatically registers sensor
records** for actual, supported numeric packet fields, requiring no sensor UUID
map or manually entered hardware identifier. Internal database keys still
exist for safe persistence and provenance; users do not configure them.

## Raspberry Pi runtime configuration

The Raspberry Pi still needs a configured AquaMind system and an attached USB
ESP32 sending valid `aquamind_sensor` schema-v1 JSON packets.

```ini
ESP32_SERIAL_ENABLED=true
ESP32_SERIAL_PORT=/dev/serial/by-id/YOUR_ACTUAL_ESP32_USB_DEVICE
ESP32_SERIAL_BAUDRATE=115200
ESP32_DEVICE_ID=esp32-devkit-01
ESP32_SYSTEM_ID=YOUR_AQUAMIND_SYSTEM_UUID

# Optional automatic database history/alert integration:
ESP32_SENSOR_BRIDGE_ENABLED=true
```

`ESP32_DEVICE_ID` and `ESP32_SYSTEM_ID` are **backend transport safety
settings** and are not shown on the website. No
`ESP32_SENSOR_MAP_JSON` setting is needed. These identifiers tie incoming
packets to the correct authenticated AquaMind system and prevent mixing data
from unrelated devices. The bridge is **disabled by default** until deliberately
enabled on the Raspberry Pi. The ordinary Sensors live view reads already
archived ESP32 packets and does not require enabling the registered sensor
bridge.

Keep Raspberry Pi GPIO/relay hardware control disabled:
`HARDWARE_ENABLED=false`. The water pump is independently powered;
the fish-feeding servo has its own separate planned command transport.

## Field discovery

For a new accepted packet with a real usable value, the bridge resolves or
creates an internal sensor record automatically. Supported numeric fields:

| Sensor | ESP32 field | Unit |
|---|---|---|
| Water temperature | `water_temp_c` | °C |
| pH | `ph` | pH |
| TDS | `tds_ppm` | ppm |
| Water level | `water_level_pct` | % |
| Water height | `water_height_cm` | cm |
| Ultrasonic distance | `distance_cm` | cm |
| Air temperature | `air_temp_c` | °C |
| Humidity | `humidity_pct` | % |

The bridge does not create measurements for null fields or fields with a
device-reported raw read failure. It does not reenable disabled/deleted
registered sensors, trust simulator devices, or claim a physically
disconnected probe is active. Existing device-field registration cannot be
silently reassigned to another system.

## pH and TDS remain calibration-gated

A non-null `ph` or `tds_ppm` value is **not sufficient** to create a trusted
registered reading. Even if firmware claims it is calibrated, the registered
sensor is automatically created with `calibration_status=pending`. Before
using it for registered history/alerts, an administrator must verify the real
probe against reference solutions and record the corresponding verified
calibration on the registered sensor, including the ESP32 device and confirmation
that the firmware calibration was applied. The bridge never promotes
`ph_unverified_estimate`, `tds_unverified_ppm`, or raw voltages into
trusted readings. The simplified Sensors page also hides uncalibrated values
instead of calling them active.

## Freshness and reliability

- **Active** means a recent packet contained a usable numeric measurement;
  it does not physically prove sensor accuracy.
- If no packet arrives recently, the UI hides old measurements and indicates
  that current sensor readings are unavailable.
- The ESP32 packet archive and sensor/alert transaction are atomic when
  the bridge is enabled; exact retries do not duplicate histories.
- No GPIO actuator, external pump, relay, or feeder servo is controlled by
  this sensor bridge.
- Actual on-device commissioning is still required. CI tests operate with
  synthetic packet fixtures, not real probes or the Raspberry Pi.

## Commissioning

1. Confirm ESP32 USB packets appear on the dashboard in the full diagnostic view.
2. Open **Sensors**: active water-temperature/air-temperature/humidity
   measurements will appear without configuring sensor identifiers.
3. With the bridge still disabled, confirm that recent packets, units and
   raw read errors reflect actual hardware.
4. If sensor history and threshold alerts are needed, enable
   `ESP32_SENSOR_BRIDGE_ENABLED=true` and restart AquaMind.
5. Confirm registered sensor records and readings appear automatically
   in the backend, with no manual UUID map.
6. Verify pH/TDS calibration before enabling those values for alerts.
7. Disconnect ESP32 USB and confirm the UI **does not label old readings Active**.

Internal sensor identifiers remain in the database for reconciliation, audit
logs and historical detail links; they are deliberately not part of the normal
Sensors UI or manual setup.
