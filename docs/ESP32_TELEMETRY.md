# ESP32 over USB serial → Raspberry Pi 5 → AquaMind

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
cards, unverified voltage diagnostics, and the last 10 records. It polls
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
