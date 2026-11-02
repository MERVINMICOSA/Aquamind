# ESP32 packet ingestion (AquaMind schema v1)

This feature accepts the **existing** ESP32 JSON body unchanged, stores it as a complete historical packet in PostgreSQL, and displays it in the signed-in AquaMind dashboard. It does **not** alter the existing individual sensor read/write APIs, sensor-based automations, or the Raspberry Pi hardware execution switch.

## Database migration

On the Raspberry Pi, with the AquaMind Python virtual environment activated and PostgreSQL configured, from the backend directory:

~~~sh
alembic upgrade head
~~~

The migration creates the esp32_telemetry table with the original JSON packet, server timestamp, configured system association, and a unique identity across (system, device_id, sequence, uptime_ms). Existing migrations remain intact.

## Private server configuration

Set these variables in the Raspberry Pi backend's **private runtime environment**, not on GitHub:

~~~dotenv
ESP32_INGEST_TOKEN=GENERATE_A_UNIQUE_RANDOM_TOKEN_OF_AT_LEAST_32_CHARACTERS
ESP32_DEVICE_ID=esp32-devkit-01
ESP32_SYSTEM_ID=YOUR_EXISTING_AQUAPONICS_SYSTEM_UUID
~~~

Generate a token using:

~~~sh
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
~~~

Find the system UUID from the protected GET /api/v1/systems API after logging into AquaMind. Configuration is required: the endpoint fails closed with HTTP 503 rather than accepting anonymous telemetry. Restart the backend after setting environment variables; the values are read at startup. Use a different secret from JWT or admin credentials.

The application does not create a new system automatically and does not need HARDWARE_ENABLED=true: ESP32 transmissions work when Raspberry Pi GPIO hardware execution is disabled. Never put the ingestion token in frontend VITE_* variables.

## ESP32 HTTP request

- Method: POST
- URL: https://YOUR-PI-OR-REVERSE-PROXY/api/v1/esp32/telemetry
- Header: Content-Type: application/json
- Header: X-ESP32-Token: <the private ESP32 token>
- Body: the exact v1 aquamind_sensor object, including nullable values

Example body:

~~~json
{
  "type": "aquamind_sensor",
  "schema_version": 1,
  "device_id": "esp32-devkit-01",
  "sequence": 5,
  "uptime_ms": 15023,
  "water_temp_c": 27.56,
  "ph_voltage_v": 0.559,
  "ph_unverified_estimate": 17.45,
  "ph_calibrated": false,
  "ph": null,
  "tds_voltage_v": 2.435,
  "tds_unverified_ppm": 1249,
  "tds_calibrated": false,
  "tds_ppm": null,
  "distance_cm": null,
  "water_height_cm": null,
  "water_level_pct": null,
  "air_temp_c": 27.67,
  "humidity_pct": 84.60
}
~~~

Replies: 201 on new save, 200 on exact retry, 401 if token missing/wrong, 403 for wrong device_id, 422 for invalid schema or measurement, 409 if the same packet identity arrives with different content. A genuinely new packet needs a new sequence and/or uptime combination. **With v1's lack of boot_id**, an unlikely same-identity collision after reboot can be rejected; a future firmware schema version should add a boot/session identifier.

**Security:** Use HTTPS where possible. If TLS is not available on the ESP32, keep the Raspberry Pi and device on an isolated trusted LAN/VLAN: plain HTTP exposes the device token to observers. Limit network access to the ingestion port. Do not log the request header or commit firmware containing a production token. Rotate on suspicion of exposure.

## Dashboard and history

The signed-in AquaMind dashboard for the configured system shows the latest received ESP32 packet, a panel of measurements, unverified voltage/estimate diagnostics, and ten recent packet records, refreshing approximately every 10 seconds.

- GET /api/v1/esp32/telemetry/latest?system_id=UUID -> latest packet or null
- GET /api/v1/esp32/telemetry?system_id=UUID&limit=10&offset=0 -> bounded saved packet history

Read endpoints require AquaMind admin authentication (JWT). All fields are saved, including null ultrasonic values; the dashboard says "No reading" rather than zero.

**Calibration safety:** The supplied 17.45 is **not a valid calibrated pH**. The unverified pH/TDS estimates are retained and labeled as diagnostic guesses, and when ph_calibrated/tds_calibrated are false their authoritative pH/TDS values must be null. These packets do not populate the canonical sensor_readings table or trigger alert/automation rules. Mapping genuinely calibrated physical measurements into canonical Sensor records is a separate, controlled integration task.

## Verification

~~~sh
cd backend
pytest -q tests/test_esp32_telemetry_api.py
cd ../frontend
npm test -- --run src/components/dashboard/Esp32TelemetryPanel.test.tsx src/services/esp32TelemetryService.test.ts
npm run build
~~~

The firmware itself must send a POST request to this endpoint; sending the JSON only to a serial monitor does not transmit it to AquaMind.
