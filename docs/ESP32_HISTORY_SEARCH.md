# Searching saved ESP32 sensor readings

AquaMind's **History** page searches archived ESP32 USB measurements in
PostgreSQL. It is read-only and does **not** alter feeding schedules, pumps,
relays, or stored sensor/packet values.

## What is searchable

Navigate to **History** in the sidebar, or choose **Search past readings**
from Dashboard or Sensors.

Choose the aquaponics system and sensor, optionally specify:

- **From date / To date:** local calendar dates; the end date is inclusive
  on screen, converted to an exclusive next-day boundary for the API
- **Minimum / Maximum value:** numeric sensor value filter
- **Previous / Next page:** browse all matching archived packets, 25 at a time
- **Refresh:** fetch current saved records without resetting the filters

The first page automatically refreshes every 15 seconds, while older pages
remain stable for review. The chart displays measurements on the **currently
loaded page**; it does not imply that all months of data were loaded into
your browser. The timestamp displayed is when the Raspberry Pi **received**
the packet, not the ESP32 measurement timestamp (protocol v1 has no UTC
measurement time).

### Supported measurements

Water temperature, air temperature, humidity, water-level percentage,
water height, ultrasonic distance, and device-reported pH / TDS.

Archived pH and TDS values are **firmware claims, not independently verified
calibration results**. They are labeled as device reported and must not
be treated as trusted water-quality readings, even if the ESP32 packet
claims calibration. Unverified voltage/estimated fields are never silently
converted into calibrated measurements.

If a packet has a later explicit raw-read fault, its value is marked as
faulty rather than being silently reported as a good measurement.

## API

The new endpoint is authenticated:

`GET /api/v1/esp32/telemetry/search`

Query parameters:

| Name | Description |
| --- | --- |
| `system_id` | Required aquaponics system UUID |
| `field` | Required allowlisted ESP32 measurement name |
| `start_at` | Optional timezone-aware ISO 8601 timestamp (inclusive) |
| `end_at` | Optional timezone-aware ISO 8601 timestamp (exclusive) |
| `min_value` | Optional numeric minimum |
| `max_value` | Optional numeric maximum |
| `limit` | Per-page result count 1–100 (default 25) |
| `offset` | Number of matching rows skipped (default 0) |

The response contains `items`, `total`, `limit`, and `offset`.
All constraints run in the database **before** pagination and remain
scoped to the requested system. Date ranges must have timezone offsets
and be ordered correctly. Invalid fields are rejected.

The original `/esp32/telemetry` endpoint stays unchanged for existing
dashboard clients. No schema migration or ingestion firmware change is
required.

## Raspberry Pi deployment

AquaMind is served by Nginx from `/var/www/aquamind`, while source/build
lives under `~/Desktop/Aquamind/frontend`.

```bash
cd ~/Desktop/Aquamind
git pull --ff-only origin main

sudo systemctl restart aquamind
sudo systemctl status aquamind --no-pager

cd frontend
npm ci
npm run build
sudo cp -a /var/www/aquamind "/var/www/aquamind.backup.$(date +%Y%m%d-%H%M%S)"
sudo cp -a dist/. /var/www/aquamind/
sudo nginx -t && sudo systemctl reload nginx
```

After deployment, reload the site without cache and visit **History**.
The ESP32 USB port must be working for **new** data to arrive, but past
packets remain searchable even while the ESP32 is disconnected.
