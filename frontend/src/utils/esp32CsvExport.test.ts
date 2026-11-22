import { describe, expect, it } from 'vitest'
import type { Esp32Telemetry } from '../types/esp32Telemetry'
import { buildEsp32HistoryCsv } from './esp32CsvExport'

const item: Esp32Telemetry = {
  id: 'packet-one', system_id: 'system-1', received_at: '2026-11-22T10:00:00Z',
  packet: {
    type: 'aquamind_sensor', schema_version: 1, device_id: 'esp32-devkit-01',
    sequence: 12, uptime_ms: 30000,
    water_temp_c: 27.1, ph_voltage_v: .5, ph_unverified_estimate: 17.4,
    ph_calibrated: false, ph: null,
    tds_voltage_v: 2.4, tds_unverified_ppm: 1249,
    tds_calibrated: false, tds_ppm: null,
    distance_cm: null, water_height_cm: null, water_level_pct: null,
    air_temp_c: 29, humidity_pct: 65,
    raw_readings: { ultrasonic: { status: 'read_error', error_code: 'no_echo' } },
  },
}

describe('ESP32 history CSV export', () => {
  it('exports all measurements, missing calibration, and raw read failures', () => {
    const csv = buildEsp32HistoryCsv([item], 'all')
    expect(csv).toContain('"Water temperature (C)"')
    expect(csv).toContain('"TDS (ppm, device reported) status"')
    expect(csv).toContain('"2026-11-22T10:00:00Z"')
    expect(csv).toContain('"Not calibrated"')
    expect(csv).toContain('"Sensor read: read error"')
    expect(csv).not.toContain('1249')
    expect(csv).not.toContain('17.4')
  })
  it('exports only the chosen measurement for an individual sensor filter', () => {
    const csv = buildEsp32HistoryCsv([item], 'humidity_pct')
    expect(csv).toContain('"Humidity (%)"')
    expect(csv).not.toContain('"Water temperature (C)"')
    expect(csv).toContain(',65,"Recorded"')
  })
  it('escapes commas, quotes and potentially dangerous spreadsheet values', () => {
    const csv = buildEsp32HistoryCsv([
      { ...item, packet: { ...item.packet, device_id: '=HYPERLINK("example","test"),extra' } },
    ], 'all')
    expect(csv).toContain('"\'=HYPERLINK(""example"",""test""),extra"')
  })
})
