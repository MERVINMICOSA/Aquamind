# Imported validation history

The workbook `DATE` and `TIME` columns describe intended Philippine validation clock times. The CSV used a UTC suffix for these clock times. Revision 5e91ab2c7d40 assigns a separate validation_at for the specifically labeled test-esp32-devkit-01 import, subtracting eight hours only where validation_at is null. Original received_at, packet, sequence, and uptime remain unchanged. This is an imported schedule, not verified receipt time.

Sensor History uses validation_at when present, otherwise received_at; searches and displayed history times use Asia/Manila. CSV retains original data, an explicit PHT display time, source and manual correction log. Original-value charts and threshold warnings still use original measurements, not manual corrections.

Administrators can append a documented numeric correction to an individual record. The original packet remains immutable, and the correction contains the reason, original value, editor ID and server timestamp. No raw diagnostics or calibration claims are changed. Corrections are displayed in a separate column and included in CSV. The migration does not delete readings. Back up the database before migrating; downgrading requires restoring the pre-migration backup.

Deploy with the existing service configuration: stop the service, back up the database, run Alembic upgrade head in the configured backend environment, build and publish the frontend, then restart the service and verify history. Keep the ESP32 disconnected until verified.
