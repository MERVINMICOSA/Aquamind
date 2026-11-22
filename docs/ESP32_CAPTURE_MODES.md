# ESP32 Live and Timed History Capture

## Behavior

The Raspberry Pi accepts valid `aquamind_sensor` JSON packets continuously over the configured USB serial port. The authenticated `GET /api/v1/esp32/telemetry/latest?system_id=...` endpoint reads the newest received packet from a **single bounded state row**. The Dashboard and Sensors page use that live endpoint; the History page and CSV export use only archived packets.

In **Live** mode, each distinct valid incoming packet is archived. In **Timed** mode, the Raspberry Pi's one-second scheduler stores only the last accepted, fresh packet received **before** each boundary. Server receipt time is authoritative because ESP32 schema v1 has no trusted wall clock. The archive retains the packet's **original receipt timestamp**. Timer deadlines and the timestamp of the last saved packet are stored in PostgreSQL and survive Raspberry Pi restarts.

The system does not create readings at exact interval timestamps: if a packet arrived at 10:04:58 and a five-minute timer expires at 10:05:00, history stores the 10:04:58 packet. It never relabels it as measured at 10:05:00.

## Reliability safeguards

- The archived ESP32 identity remains unique on system, device, sequence, and uptime. A bounded, persistent 32-packet fingerprint window rejects short replay bursts even when those packets were not archived.
- Only successfully validated sensor JSON is accepted. Null sensor values and diagnostic failures are retained as sent; pH/TDS estimates never become calibrated readings.
- The scheduled boundary is processed under a database row lock and before a new incoming packet can replace the previous one. A separate timer still works when serial input stops.
- An interval with no eligible fresh packet is **skipped**. A packet more than 45 seconds old at the deadline is not reused. A disconnected ESP32 cannot repeatedly generate historical entries.
- Elapsed deadlines after a server restart are advanced without retroactive data fabrication. Changing mode or interval starts a new window immediately, preserving previously archived history.
- The latest live record has bounded storage regardless of reporting frequency. Timed mode reduces archived/history record growth, but the latest-state row is updated on every accepted packet, so it does **not** eliminate per-packet database I/O.
- Sensor bridge readings and calibration-dependent threshold processing are derived only when a packet is actually archived, preserving the existing automation safety boundaries.
- The collection settings API requires a signed-in user to read and an administrator to modify. Inputs are validated (Live or Timed, 1–1440 minutes). No USB serial token or device credential is exposed to the website.

## API and UI

- `GET /api/v1/esp32/capture?system_id=<uuid>`: current mode, device, interval, newest reception, last saved packet and next scheduled save.
- `PUT /api/v1/esp32/capture?system_id=<uuid>`: administrator-only JSON, e.g. `{"mode":"timed","interval_minutes":5}`. Select Live with `{"mode":"live","interval_minutes":5}`.
- `GET /api/v1/esp32/telemetry/latest`: most recent accepted USB packet; if upgrading from earlier database history, archived latest remains visible until a new packet arrives.
- `GET /api/v1/esp32/telemetry` and `.../search`: saved history only.

On the website select **Settings → ESP32 data collection**. Live saves all accepted packets, while Timed offers preset and custom intervals plus a countdown and last-received/last-saved status.

Existing installations default to **Live** for backward compatibility until an administrator explicitly selects Timed; the recommended routine setting is **Timed, five minutes**.

## Deployment

1. Back up PostgreSQL before upgrading.
2. Pull the feature branch (or merge its PR into main), activate the backend virtual environment, and run `alembic upgrade head` **before restarting AquaMind**. The service requires the new `esp32_capture_state` table.
3. Restart the `aquamind` systemd service and confirm `sudo systemctl status aquamind` / `sudo journalctl -u aquamind -n 100 --no-pager` show a healthy serial worker and no database errors.
4. Run the frontend build (`npm ci && npm run build`) and publish the resulting built assets to the actual Nginx document root used on the Raspberry Pi.
5. Verify the ESP32 firmware is **continuously transmitting**: earlier experimental firmware used a 30-minute reporting interval. This website feature changes database archiving, not the firmware's transmission cadence.
6. Test Live: multiple distinct USB packets appear in History. Test Timed: the dashboard changes continuously while history only grows at the chosen boundaries. Unplug the ESP32 across a deadline to verify no stale history is inserted; reconnect and verify the next fresh interval.
7. If using multiple API processes, ensure exactly one process owns the USB serial worker. The Postgres row lock serializes capture updates, but multiple USB readers must not compete for the same serial port.

### Automated tests

Backend: `pytest backend/tests/test_esp32_capture.py backend/tests/test_esp32_serial_service.py` (run from a configured test environment with the backend on the Python path).

Frontend: `cd frontend && npm test -- --run` and `npm run build`.

The GitHub branch is not deployed to the Raspberry Pi merely by being pushed.
