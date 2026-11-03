/**
 * Browser-only SAMPLE fixtures for previewing the dashboard layout.
 * Never POST or persist these to AquaMind. No actuator commands can use them.
 */
import type {
  AquaponicsSystem,
  DashboardActuator,
  DashboardAlert,
  DashboardSensor,
  DashboardSensorReading,
} from '../types/dashboard'
import type { ActuatorEvent } from '../services/actuatorService'
import type { Esp32Telemetry } from '../types/esp32Telemetry'

const SYSTEM_ID = 'demo-only-aquamind'
const DEMO_DEVICE_ID = 'demo-esp32-not-connected'
const iso = (ms: number) => new Date(ms).toISOString()

const specs = [
  { id: 'water-temp', name: 'Fish tank water temperature', type: 'water_temperature', kind: 'temperature', unit: '°C', value: 27.4 },
  { id: 'ph', name: 'Fish tank pH', type: 'ph', kind: 'acidity', unit: 'pH', value: 7.1 },
  { id: 'tds', name: 'Grow-bed TDS', type: 'tds', kind: 'concentration', unit: 'ppm', value: 780 },
  { id: 'water-level', name: 'Water level', type: 'water_level', kind: 'level', unit: '%', value: 68 },
  { id: 'air-temp', name: 'Grow area air temperature', type: 'air_temperature', kind: 'temperature', unit: '°C', value: 29.2 },
  { id: 'humidity', name: 'Grow area humidity', type: 'humidity', kind: 'humidity', unit: '%', value: 73 },
] as const

export function buildDashboardDemo(nowMs: number) {
  const now = iso(nowMs)
  const system: AquaponicsSystem = {
    id: SYSTEM_ID,
    name: 'DEMO: Tilapia + Lettuce System',
    description: 'Illustrative dashboard layout; no actual readings',
    timezone: 'Asia/Manila',
    is_active: true,
    created_at: now,
    updated_at: now,
  }

  const sensors: DashboardSensor[] = specs.map((spec) => ({
    id: 'demo-' + spec.id,
    system_id: SYSTEM_ID,
    name: spec.name,
    sensor_type: spec.type,
    measurement_type: spec.kind,
    location_type: spec.id === 'air-temp' || spec.id === 'humidity' ? 'grow_bed' : 'tank',
    location_id: null,
    unit: spec.unit,
    hardware_identifier: null,
    is_simulated: true,
    is_enabled: true,
    sampling_interval_seconds: 30,
    calibration_status: 'verified',
    created_at: now,
    updated_at: now,
  }))

  const latestReadings: DashboardSensorReading[] = specs.map((spec, i) => ({
    id: 'demo-reading-' + spec.id,
    sensor_id: 'demo-' + spec.id,
    recorded_at: iso(nowMs - 12_000 - i * 2_000),
    value_numeric: spec.value,
    unit: spec.unit,
    quality_status: 'sample',
    source: 'simulation',
    sequence_number: i + 1,
    created_at: now,
  }))

  const actuators: DashboardActuator[] = [
    {
      id: 'demo-circulation-pump', system_id: SYSTEM_ID,
      name: 'Circulation pump', actuator_type: 'water_pump',
      control_mode: 'manual', hardware_identifier: null,
      location_type: 'tank', location_id: null,
      is_enabled: true, safety_config: null,
      current_state: 'off', current_value: null, last_state_at: now,
      created_at: now, updated_at: now, deleted_at: null,
    },
    {
      id: 'demo-feeder', system_id: SYSTEM_ID,
      name: 'Tilapia feeder', actuator_type: 'feeder',
      control_mode: 'manual', hardware_identifier: null,
      location_type: 'tank', location_id: null,
      is_enabled: true, safety_config: null,
      current_state: 'off', current_value: null, last_state_at: now,
      created_at: now, updated_at: now, deleted_at: null,
    },
  ]

  const alerts: DashboardAlert[] = [
    {
      id: 'demo-alert-water', system_id: SYSTEM_ID,
      sensor_id: 'demo-water-level', actuator_id: null,
      alert_type: 'threshold', severity: 'warning',
      message: '[SAMPLE] Reservoir level below preferred range',
      trigger_value: 25, threshold_id: null, status: 'resolved',
      created_at: iso(nowMs - 3_600_000),
      acknowledged_at: null, acknowledged_by_user_id: null,
      resolved_at: iso(nowMs - 2_400_000),
      resolution_reason: 'Demo-only sample',
    },
    {
      id: 'demo-alert-ph', system_id: SYSTEM_ID,
      sensor_id: 'demo-ph', actuator_id: null,
      alert_type: 'threshold', severity: 'info',
      message: '[SAMPLE] pH trend review',
      trigger_value: 7.1, threshold_id: null, status: 'resolved',
      created_at: iso(nowMs - 7_200_000),
      acknowledged_at: null, acknowledged_by_user_id: null,
      resolved_at: iso(nowMs - 6_000_000),
      resolution_reason: 'Demo-only sample',
    },
  ]

  return {
    systems: [system],
    selectedSystem: system,
    selectedSystemId: SYSTEM_ID,
    sensors, actuators, alerts, latestReadings,
    systemsStatus: 'ready' as const,
    overviewStatus: 'ready' as const,
    errorMessage: null,
    selectSystem: (_id: string | null) => {},
  }
}

export function buildDemoSensorTrend(sensorId: string | null, nowMs: number): DashboardSensorReading[] {
  const spec = specs.find((item) => 'demo-' + item.id === sensorId)
  if (!spec) return []

  return Array.from({ length: 12 }, (_, i) => {
    const time = nowMs - (11 - i) * 15 * 60_000
    const variation = Math.sin(i * 0.65 + specs.indexOf(spec)) *
      (spec.id === 'tds' ? 19 : spec.id === 'water-level' ? 3 : spec.id === 'humidity' ? 4 : 0.3)
    const value = Math.round((spec.value + variation) * 100) / 100
    return {
      id: 'demo-trend-' + spec.id + '-' + i,
      sensor_id: sensorId!,
      recorded_at: iso(time),
      value_numeric: value,
      unit: spec.unit,
      quality_status: 'sample',
      source: 'simulation',
      sequence_number: i,
      created_at: iso(time),
    }
  })
}

export function buildDemoActuatorEvents(actuatorId: string | null, nowMs: number): ActuatorEvent[] {
  if (!actuatorId || !actuatorId.startsWith('demo-')) return []
  return ['start', 'stop', 'start', 'stop'].map((command, i) => {
    const when = iso(nowMs - (i + 1) * 45 * 60_000)
    return {
      id: 'demo-event-' + i,
      actuator_id: actuatorId,
      command_type: command,
      requested_value: null,
      actual_value: null,
      started_at: when,
      completed_at: when,
      duration_ms: 300,
      trigger_source: 'sample_preview',
      status: 'simulated',
      fault_code: null,
      error_message: null,
      created_at: when,
    }
  })
}

export function buildDemoEsp32Packets(nowMs: number): Esp32Telemetry[] {
  return [0, 1, 2].map((i) => ({
    id: 'demo-esp32-packet-' + i,
    system_id: SYSTEM_ID,
    received_at: iso(nowMs - (i + 1) * 8_000),
    packet: {
      type: 'aquamind_sensor',
      schema_version: 1,
      device_id: DEMO_DEVICE_ID,
      sequence: 103 - i,
      uptime_ms: 240_000 + i * 2_000,
      water_temp_c: 27.4,
      ph_voltage_v: 2.32,
      ph_unverified_estimate: 7.1,
      ph_calibrated: false,
      ph: null,
      tds_voltage_v: 1.32,
      tds_unverified_ppm: 780,
      tds_calibrated: false,
      tds_ppm: null,
      distance_cm: 30.9,
      water_height_cm: 19.1,
      water_level_pct: 68,
      air_temp_c: 29.2,
      humidity_pct: 73,
      reservoir_water_present: null,
      raft2_water_present: null,
      raw_readings: {
        ph: { status: 'ok', value: 2050 + i * 3, unit: 'adc_count' },
        tds: { status: 'ok', value: 1590 + i * 4, unit: 'adc_count' },
        reservoir_level: { status: 'ok', value: 1870 + i * 2, unit: 'adc_count' },
        raft2_level: { status: 'ok', value: 1720 + i * 2, unit: 'adc_count' },
        ultrasonic: { status: 'ok', value: 1802, unit: 'microseconds' },
        water_temperature: { status: 'ok', value: 27.4, unit: 'celsius' },
        air_temperature: { status: 'ok', value: 31740, unit: 'sensor_ticks' },
        humidity: { status: 'ok', value: 41000, unit: 'sensor_ticks' },
      },
    },
  }))
}
