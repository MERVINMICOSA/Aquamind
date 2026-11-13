# ESP32 over USB serial → Raspberry Pi 5 → AquaMind

> **Optional registered sensor ingestion:** The original USB packet archive is
> unchanged. To additionally map validated packet fields into the Sensors
> page, historical charts, and threshold alerts, see
> [ESP32 sensor bridge setup](ESP32_SENSOR_BRIDGE.md). The bridge is disabled
> until explicit field-to-sensor mappings are configured and enabled. It does
> not control any pump, relay, or feeding servo.


**AquaMind now receives ESP32 JSON through the Pi's USB port, not HTTP.**
The old device-token HTTP POST has been removed. The dashboard still reads
persisted records through authenticated API GET requests.

## Physical connection

```text
ESP32 DevKit -- USB data cable --> Raspberry Pi 5
                                      |
                              pyserial serial reader
                                      |
                              FastAPI application worker
                                      |
                            PostgreSQL esp32_telemetry
                                      |
                             AquaMind web dashboard
```

The ESP32 does **not** need Wi-Fi, an API key, or its own login.
Use a USB cable supporting data, not a charge-only cable. Plug the
ESP32 into the **Raspberry Pi**, not the computer you use to browse the dashboard.

## ESP32 firmware output

Print one complete schema-v1 JSON object through `Serial` at **115200 baud**.
Either compact newline-delimited JSON or pretty-printed multiline JSON is
supported. Serial boot/debug text outside JSON objects is ignored.

ArduinoJson sketch fragment (integrate with existing sensor code):

```cpp
#include <ArduinoJson.h>

void setup() {
  Serial.begin(115200);
  // Initialize sensors as in your existing firmware.
}

void publishSensorData(JsonDocument& doc) {
  // Fill doc with your existing v1 aquamind_sensor fields.
  // Preserve JSON null for uncalibrated/absent measurements.
  serializeJson(doc, Serial);
  Serial.println();  // Packet boundary; no HTTP or Wi-Fi call.
}
```

For ESP32 firmware that already prints the JSON packet to the USB Serial
Monitor, a code change may not be required; confirm the baud rate and that
only complete JSON objects are sent. An ESP32 console attached to another
computer must be closed so the Pi can own the device. Opening USB serial may
reset some ESP32 boards; the worker reconnects automatically if unplugged.

## Raw sensor diagnostics (optional schema-v1 extension)

To diagnose a JSON `null`, the **ESP32 firmware** must send both the
sensor-native reading and the outcome of trying to read that sensor.
The Pi cannot recover an ADC count, ultrasonic echo duration, or I²C/1-Wire
fault from a processed null value. The backend accepts an optional
`raw_readings` object in otherwise unchanged schema-version-1 packets.

Example fragment to merge into an existing complete `aquamind_sensor` JSON
packet (illustrative values, **not live measurements**):

```json
{
  "raw_readings": {
    "ph": {"status": "ok", "value": 2100, "unit": "adc_count"},
    "tds": {"status": "ok", "value": 1560, "unit": "adc_count"},
    "ultrasonic": {"status": "timeout", "value": null, "unit": "microseconds", "error_code": "echo_timeout"},
    "water_temperature": {"status": "disconnected", "value": null, "unit": "celsius", "error_code": "ds18b20_disconnected"},
    "air_temperature": {"status": "ok", "value": 27.67, "unit": "celsius"},
    "humidity": {"status": "ok", "value": 84.6, "unit": "percent"}
  }
}
```

Supported sensor keys: `ph`, `tds`, `ultrasonic`, `water_temperature`,
`air_temperature`, and `humidity`. Each key is optional for compatibility,
but firmware should report all installed/expected sensors so the operator can
distinguish a silent device from an explicit fault.

- `status: "ok"` means a device-side read returned `value`, **not** that the
  probe is calibrated or physically verified. A raw ADC value of **0 is valid
  data**, distinct from JSON `null`. Analog reads can return numeric values
  even when probes are disconnected or floating.
- `status: "not_configured"` means firmware intentionally disabled that
  sensor; `disconnected` means firmware **detected** disconnection;
  `timeout` means a timed-out read; `read_error` means another failed read.
  These failures must not include a numeric `value`.
- If no sensor diagnostic is supplied, the dashboard says **Not reported**,
  not **Disconnected** or **Reading OK**.
- `unit` may be `adc_count`, `microseconds`, `celsius`, `percent`,
  `sensor_ticks`, or `volts`. `error_code` is an optional short device-side
  machine-readable identifier such as `echo_timeout`.
- Raw diagnostics do **not** authorize uncalibrated `ph` or `tds_ppm`.
  Keep those fields `null` when `ph_calibrated=false` /
  `tds_calibrated=false`. Existing top-level `ph_voltage_v` and
  `tds_voltage_v` remain available.
- When using SHT40/DS18B20 libraries, a decoded temperature or humidity
  returned by the sensor library can be reported in `celsius`/`percent`;
  do not call it an ADC count unless you actually read ADC hardware.

ArduinoJson integration sketch (illustrative; use the actual configured
pins and sensor library calls in your existing firmware):

```cpp
// doc is the same JSON document containing the full required v1 packet.
// PH_ADC_PIN and TDS_ADC_PIN must already be defined for your wired ESP32.
JsonObject raw = doc["raw_readings"].to<JsonObject>();
JsonObject phRaw = raw["ph"].to<JsonObject>();
phRaw["status"] = "ok";  // analogRead executed; NOT proof the probe is good
phRaw["value"] = analogRead(PH_ADC_PIN);
phRaw["unit"] = "adc_count";

JsonObject tdsRaw = raw["tds"].to<JsonObject>();
tdsRaw["status"] = "ok";
tdsRaw["value"] = analogRead(TDS_ADC_PIN);
tdsRaw["unit"] = "adc_count";

// Set ultrasonic status based on the *actual* echo timing result.
// For pulseIn(), 0 indicates no pulse before timeout; don't report it
// as a measured zero-centimeter distance.
JsonObject echoRaw = raw["ultrasonic"].to<JsonObject>();
unsigned long echoUs = pulseIn(ECHO_PIN, HIGH, 30000);
echoRaw["unit"] = "microseconds";
if (echoUs == 0) {
  echoRaw["status"] = "timeout";
  echoRaw["value"] = nullptr;
  echoRaw["error_code"] = "echo_timeout";
  doc["distance_cm"] = nullptr;
} else {
  echoRaw["status"] = "ok";
  echoRaw["value"] = echoUs;
}

// Report DS18B20/SHT40 errors only after checking your actual library's
// return values, sentinel values, CRC/status codes, or connection flags.
// Never claim "ok" for an unattempted read, or invent a raw value.
```

The serial receiver validates and stores these optional diagnostics
alongside the original measurements in PostgreSQL's existing JSON
`esp32_telemetry.packet` column; **no new migration is necessary**.
The signed-in dashboard shows status/raw value/error per sensor for the
latest packet, plus recent pH/TDS raw counts and ultrasonic status.
Old history without `raw_readings` stays readable and shows **Not reported**.

## Reservoir and lower raft red analog water-presence probes

For the common three-pin red S/+/- resistive sensors, connect **S** to
ESP32 GPIO32 (reservoir) or GPIO33 (second raft), **+** to **3V3** and **-**
to **GND**. Those are ADC1 inputs, independent of pH GPIO35 and TDS GPIO34.
Ensure the exposed conductive traces only touch the water at the intended
presence-detection height; keep the connector above the waterline.

The ESP32 can report these two raw sensor-native values under:

```json
"raw_readings": {
  "reservoir_level": {"status": "ok", "value": 415, "unit": "adc_count"},
  "raft2_level": {"status": "ok", "value": 1980, "unit": "adc_count"}
},
"reservoir_water_present": null,
"raft2_water_present": null
```

This is an illustrative **fragment**, not a complete packet or verified
wet/dry reading. `raw_readings.reservoir_level` and
`raw_readings.raft2_level` are optional alongside existing sensor keys.
Boolean `reservoir_water_present` and `raft2_water_present` are optional
and **null until the respective firmware threshold has been determined by
measuring dry and wet raw ADC counts at the actual installation**. Once
calibrated, firmware may send true (wet) or false (dry).
A raw ADC reading of 0 is a numeric value, not `null`. An analog reading
marked `ok` only means the ADC conversion completed: these resistive probes
cannot reliably self-diagnose disconnection and are susceptible to corrosion,
fouling, salt/mineral deposits and splashes. Do **not** use the new readings
alone for unattended dry-run pump protection.

This optional schema-v1 extension uses the same existing JSON telemetry
storage. Older device packets and database rows remain valid; they show
unknown presence and 'Not reported' raw data. Pump control remains disabled
and independent of these USB telemetry values.

## Find your Linux serial port

With the ESP32 attached to Raspberry Pi:

```bash
ls -l /dev/serial/by-id/
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

Prefer the **stable** `/dev/serial/by-id/usb-...` path, when available, rather
than assuming `/dev/ttyUSB0` or `/dev/ttyACM0`. The name and enumeration
depend on the USB-UART chip/board.

Check permissions under your AquaMind service user:

```bash
groups
ls -l /dev/ttyUSB0  # change this to the actual device
```

On Raspberry Pi OS, USB serial permissions typically belong to the
`dialout` group. If needed, use `sudo usermod -aG dialout mervin` (replace
`mervin` with your AquaMind service user), then log out/in and restart the
service. **Do not use `chmod 777` or run the entire API as root.**

## Configure the Raspberry Pi backend

Run database migration **once** with the Pi's PostgreSQL connection:

```bash
cd ~/aquamind/backend
source .venv/bin/activate
python -m pip install -r requirements-pi.txt
alembic upgrade head
```

Configure these variables in a **private** `~/aquamind/backend/.env` file
(or the systemd unit's private environment file), not in Git:

```dotenv
ESP32_SERIAL_ENABLED=true
ESP32_SERIAL_PORT=/dev/ttyUSB0
ESP32_SERIAL_BAUDRATE=115200
ESP32_DEVICE_ID=esp32-devkit-01
ESP32_SYSTEM_ID=YOUR_EXISTING_AQUAPONICS_SYSTEM_UUID
```

Replace the port with your actual device path. Copy your existing system UUID
from the AquaMind system record (GET `/api/v1/systems` after login).
AquaMind will not create or select a system implicitly, preventing data
from being assigned to the wrong tank.

Restart the running AquaMind backend (for a systemd installation,
`sudo systemctl restart aquamind`). Run only **one** API worker process
that owns the serial port. Do not use auto-reload or multiple Uvicorn workers
on a live serial deployment. Ensure that the backend is running from the
directory where its `.env` can be loaded, or configure systemd environment
variables explicitly.

`ESP32_SERIAL_ENABLED=false` is the default and does not open hardware.
USB sensor ingestion remains independent of `HARDWARE_ENABLED`: you do not
have to enable actuator GPIO access.

## Data acceptance and persistence

The USB reader checks `type=aquamind_sensor`, `schema_version=1`,
the configured `device_id`, field ranges, finite numeric values, and pH/TDS
calibration consistency. It stores the **complete packet** in the existing
`esp32_telemetry` database table with a Pi-side receive timestamp. Missing
ultrasonic readings remain JSON `null`, not 0. The reader supports fragmented,
compact, and multiline JSON frames, bounds packet size, and retries after
temporary disconnect.

Exact retransmissions are deduplicated by
(system UUID, device ID, sequence, uptime_ms); conflicts are rejected.
With v1's lack of a boot/session identifier, some packets after an ESP32
reboot can collide if sequence and uptime repeat. A future firmware version
should include a boot/session ID.

**Important:** `ph_unverified_estimate=17.45` is not a valid calibrated
pH value. The estimate and raw pH/TDS voltages are displayed as diagnostics;
`ph`/`tds_ppm` must remain `null` until calibrated. ESP32 telemetry
does **not** populate canonical sensor readings or trigger pump automation.

## Dashboard access and diagnostics

The signed-in dashboard displays the latest packet, eight measurement
cards, unverified voltage diagnostics, optional raw read diagnostics, and the last 10 records. It polls
approximately every 10 seconds.

Protected read-only API endpoints:

- `GET /api/v1/esp32/telemetry/latest?system_id=UUID`
- `GET /api/v1/esp32/telemetry?system_id=UUID&limit=10&offset=0`

The former public-device `POST /api/v1/esp32/telemetry` route is removed;
POST requests return HTTP 405. The dashboard still requires normal
AquaMind account authentication.

Check receiver logs:

```bash
sudo journalctl -u aquamind -n 100 --no-pager
```

If the device is not detected: verify data-capable USB cable, port, baud,
service user group permissions, private env settings, and that no Serial
Monitor or other process has opened the same port.

## Tests

```bash
cd backend
python -m pytest -q tests/test_esp32_serial_service.py tests/test_esp32_telemetry_api.py
```
