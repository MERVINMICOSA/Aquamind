import { describe, expect, it } from 'vitest'
import type { SystemDashboardOverview, DashboardSensor } from '../types/dashboard'
import type { Esp32Telemetry } from '../types/esp32Telemetry'
import {
  archiveSensorId,
  archivedTrendReadings,
  mergeDashboardEsp32Archive,
  parseArchiveSensorId,
} from './esp32DashboardReadings'

const empty: SystemDashboardOverview = {
  sensors: [], actuators: [], alerts: [], latestReadings: [],
}

const packet: Esp32Telemetry = {
  id: 'packet-1',
  system_id: 'system-a',
  received_at: '2026-11-14T00:00:00Z',
  packet: {
    type: 'aquamind_sensor', schema_version: 1,
    device_id: 'esp32-devkit-01', sequence: 10, uptime_ms: 32100,
    water_temp_c: 27.56,
    ph_voltage_v: 1.7, ph_unverified_estimate: 17.45,
    ph_calibrated: false, ph: null,
    tds_voltage_v: 2.4, tds_unverified_ppm: 1249,
    tds_calibrated: false, tds_ppm: null,
    distance_cm: null, water_height_cm: null, water_level_pct: null,
    air_temp_c: 27.67, humidity_pct: 84.6,
  },
}

function sensor(name: string, identifier: string, overrides: Partial<DashboardSensor> = {}): DashboardSensor {
  return {
    id: 'registered-1',
    system_id: 'system-a', name,
    sensor_type: 'water_temperature', measurement_type: 'temperature',
    location_type: 'tank', location_id: null,
    unit: '°C', hardware_identifier: identifier,
    is_simulated: false, is_enabled: true,
    sampling_interval_seconds: 30, calibration_status: 'pending',
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-01T00:00:00Z',
    ...overrides,
  }
}

describe('ESP32 archive-derived dashboard data', () => {
  it('fills main dashboard cards from PostgreSQL packet archive without sensor registrations', () => {
    const data = mergeDashboardEsp32Archive(empty, [packet], 'system-a')
    expect(data.sensors.map(s => s.name)).toEqual([
      'Water temperature', 'Air temperature', 'Humidity',
    ])
    expect(data.latestReadings.map(r => r.value_numeric)).toEqual([27.56, 27.67, 84.6])
    expect(data.latestReadings.every(r => r.source === 'hardware')).toBe(true)
    expect(data.latestReadings.every(r => r.quality_status === 'good')).toBe(true)
    expect(data.latestReadings[0]?.recorded_at).toBe(packet.received_at)
    expect(empty.sensors).toEqual([])
    expect(empty.latestReadings).toEqual([])
  })

  it('rejects wrong-system archive records without leaking data', () => {
    expect(mergeDashboardEsp32Archive(empty, [packet], 'system-b')).toEqual(empty)
  })

  it('rejects unverified pH and TDS even if the device claims calibration', () => {
    const claimed: Esp32Telemetry = {
      ...packet,
      packet: {
        ...packet.packet,
        ph_calibrated: true, ph: 7.1,
        tds_calibrated: true, tds_ppm: 1000,
      },
    }
    const data = mergeDashboardEsp32Archive(empty, [claimed], 'system-a')
    expect(data.sensors.map(s => s.sensor_type)).not.toContain('ph')
    expect(data.sensors.map(s => s.sensor_type)).not.toContain('tds')
    expect(data.latestReadings).toHaveLength(3)
  })

  it('never promotes explicit failed device reads or null fields, but accepts zero', () => {
    const faulty: Esp32Telemetry = {
      ...packet,
      packet: {
        ...packet.packet, water_temp_c: 25.2, humidity_pct: 0,
        raw_readings: {
          water_temperature: { status: 'disconnected', error_code: 'missing' },
          humidity: { status: 'ok', value: 0, unit: 'percent' },
        },
      },
    }
    const data = mergeDashboardEsp32Archive(empty, [faulty], 'system-a')
    expect(data.sensors.map(s => s.name)).toEqual(['Air temperature', 'Humidity'])
    expect(data.latestReadings.find(r => r.unit === '%')?.value_numeric).toBe(0)
  })

  it('uses the newest packet, not an older packet to disguise a new probe failure', () => {
    const older: Esp32Telemetry = {
      ...packet, id: 'older', received_at: '2026-11-13T23:59:59Z',
    }
    const newest: Esp32Telemetry = {
      ...packet, id: 'newest', received_at: '2026-11-14T00:00:10Z',
      packet: {
        ...packet.packet,
        water_temp_c: null, air_temp_c: null, humidity_pct: null,
      },
    }
    const data = mergeDashboardEsp32Archive(empty, [older, newest], 'system-a')
    expect(data.latestReadings).toEqual([])
  })

  it('uses a matching registered physical sensor without making a second virtual card', () => {
    const existing = sensor('Tank water sensor', 'esp32-devkit-01:water_temp_c')
    const data = mergeDashboardEsp32Archive({
      ...empty,
      sensors: [existing],
    }, [packet], 'system-a')
    expect(data.sensors).toHaveLength(3)
    expect(data.latestReadings.find(r => r.sensor_id === existing.id)?.value_numeric).toBe(27.56)
    expect(data.sensors.filter(s => s.sensor_type === 'water_temperature')).toHaveLength(1)
  })

  it('never overwrites newer registered readings', () => {
    const existing = sensor('Tank water sensor', 'esp32-devkit-01:water_temp_c')
    const saved = {
      id: 'existing-reading', sensor_id: existing.id,
      recorded_at: '2026-11-14T00:01:00Z', value_numeric: 28.25,
      unit: '°C', quality_status: 'good', source: 'hardware',
      sequence_number: 12, created_at: '2026-11-14T00:01:00Z',
    }
    const data = mergeDashboardEsp32Archive({
      ...empty,
      sensors: [existing],
      latestReadings: [saved],
    }, [packet], 'system-a')
    expect(data.latestReadings.find(r => r.sensor_id === existing.id)).toEqual(saved)
  })

  it('does not override an explicitly disabled or simulated matching sensor', () => {
    for (const changed of [{ is_enabled: false }, { is_simulated: true }]) {
      const existing = sensor(
        'Water temp', 'esp32-devkit-01:water_temp_c', changed,
      )
      const data = mergeDashboardEsp32Archive({ ...empty, sensors: [existing] }, [packet], 'system-a')
      expect(data.latestReadings.filter(r => r.unit === '°C')).toHaveLength(1)
      // The single remaining °C reading is air temperature, never disabled tank.
      expect(data.latestReadings.find(r => r.sensor_id === existing.id)).toBeUndefined()
    }
  })

  it('supports a bounded historical trend from the same saved packet database', () => {
    const id = archiveSensorId('system-a', 'water_temp_c')
    const second = {
      ...packet,
      id: 'packet-2', received_at: '2026-11-14T00:00:10Z',
      packet: { ...packet.packet, water_temp_c: 27.9 },
    }
    expect(parseArchiveSensorId(id)).toEqual({ systemId: 'system-a', field: 'water_temp_c' })
    expect(parseArchiveSensorId('random-uuid')).toBeNull()
    expect(archivedTrendReadings([packet, second], id).map(r => r.value_numeric)).toEqual([27.56, 27.9])
    expect(archivedTrendReadings([packet], archiveSensorId('system-b', 'water_temp_c'))).toEqual([])
  })
})
