/** One complete packet from ESP32 firmware, schema version 1. */
export interface Esp32SensorPacket {
  type: 'aquamind_sensor'
  schema_version: 1
  device_id: string
  sequence: number
  uptime_ms: number
  water_temp_c: number | null
  ph_voltage_v: number | null
  ph_unverified_estimate: number | null
  ph_calibrated: boolean
  ph: number | null
  tds_voltage_v: number | null
  tds_unverified_ppm: number | null
  tds_calibrated: boolean
  tds_ppm: number | null
  distance_cm: number | null
  water_height_cm: number | null
  water_level_pct: number | null
  air_temp_c: number | null
  humidity_pct: number | null
}

export interface Esp32Telemetry {
  id: string
  system_id: string
  received_at: string
  packet: Esp32SensorPacket
}
