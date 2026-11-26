# Imported validation history

The workbook `DATE` and `TIME` columns describe intended Philippine validation clock times. The CSV used a UTC suffix for these clock times. Revision 5e91ab2c7d40 assigns a separate validation_at for the specifically labeled test-esp32-devkit-01 import, subtracting eight hours only where validation_at is null. Original received_at, packet, sequence, and uptime remain unchanged. This is an imported schedule, not verified receipt time.

Sensor History uses validation_at when present, otherwise received_at; searches and displayed history times use Asia/Manila. CSV retains original data, an explicit PHT display time, source and manual correction log. Original-value charts and threshold warnings still use original measurements, not manual corrections.

Sensor History is read-only. Existing correction logs remain accessible in the UI and CSV, but the manual correction write endpoint has been removed. Expandable record details distinguish the previously imported schedule from automatic receipt without a dedicated source column. Original source information remains in CSV and the database. The migration does not delete readings. Back up the database before migrating; downgrading requires restoring the pre-migration backup.

Deploy with the existing service configuration: stop the service, back up the database, run Alembic upgrade head in the configured backend environment, build and publish the frontend, then restart the service and verify history. Keep the ESP32 disconnected until verified.
