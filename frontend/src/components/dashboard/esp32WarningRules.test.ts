import { describe, expect, it } from 'vitest'
import type { Esp32SensorPacket } from '../../types/esp32Telemetry'
import { evaluateEsp32Warnings, isFreshEsp32Packet } from './esp32WarningRules'

const base: Esp32SensorPacket = {
  type: 'aquamind_sensor', schema_version: 1, device_id: 'esp32-devkit-01',
  sequence: 5, uptime_ms: 15023,
  water_temp_c: 27.56, ph_voltage_v: 0.559, ph_unverified_estimate: null,
  ph_calibrated: true, ph: 7.0,
  tds_voltage_v: 2.435, tds_unverified_ppm: null,
  tds_calibrated: true, tds_ppm: 550,
  distance_cm: 12, water_height_cm: 30, water_level_pct: 90,
  air_temp_c: 27.67, humidity_pct: 84.6,
}

describe('ESP32 advisory warning rules', () => {
  it('flags the agreed thresholds', () => {
    const warnings = evaluateEsp32Warnings({ ...base, ph: 7.9, tds_ppm: 1201, water_level_pct: 74.9 })
    expect(warnings.map(warning => warning.id)).toEqual([
      'water-level-low', 'ph-out-of-range', 'tds-high',
    ])
  })
  it('does not treat null or uncalibrated values as valid readings', () => {
    expect(evaluateEsp32Warnings({
      ...base, ph_calibrated: false, ph: 17.45,
      tds_calibrated: false, tds_ppm: 1249, water_level_pct: null,
    })).toEqual([])
  })
  it('reports actual sensor errors and suppresses thresholds from faulty reads', () => {
    const warnings = evaluateEsp32Warnings({
      ...base,
      ph: 9.0,
      water_level_pct: 10,
      raw_readings: {
        ph: { status: 'read_error', error_code: 'bad_ph' },
        ultrasonic: { status: 'timeout' },
      },
    })
    expect(warnings.map(item => item.id)).toEqual(['fault-ph', 'fault-ultrasonic'])
  })
  it('never uses old or future timestamps for live warnings', () => {
    const now = Date.parse('2026-11-22T10:00:00Z')
    expect(isFreshEsp32Packet('2026-11-22T09:59:30Z', now)).toBe(true)
    expect(isFreshEsp32Packet('2026-11-22T09:58:00Z', now)).toBe(false)
    expect(isFreshEsp32Packet('invalid', now)).toBe(false)
  })
})
