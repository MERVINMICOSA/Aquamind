import type {
  DashboardSensor,
  DashboardSensorReading,
  SystemDashboardOverview,
} from '../types/dashboard'
import type { Esp32SensorPacket, Esp32Telemetry, Esp32RawReadings } from '../types/esp32Telemetry'

/**
 * Display-only fallback for sensor packets already saved in esp32_telemetry.
 * This does not write sensor_readings or claim to validate pH/TDS calibration.
 * A real registered sensor keeps its own database ID, rules and history.
 */
export const ESP32_ARCHIVE_PREFIX = 'esp32-archive:'

const FIELD_SPECS = [
  { field: 'water_temp_c', name: 'Water temperature', sensorType: 'water_temperature', measurementType: 'temperature', unit: '°C', rawKey: 'water_temperature' },
  { field: 'water_level_pct', name: 'Water level', sensorType: 'water_level', measurementType: 'level', unit: '%', rawKey: 'ultrasonic' },
  { field: 'water_height_cm', name: 'Water height', sensorType: 'water_level', measurementType: 'level', unit: 'cm', rawKey: 'ultrasonic' },
  { field: 'distance_cm', name: 'Ultrasonic distance', sensorType: 'water_level', measurementType: 'level', unit: 'cm', rawKey: 'ultrasonic' },
  { field: 'air_temp_c', name: 'Air temperature', sensorType: 'air_temperature', measurementType: 'temperature', unit: '°C', rawKey: 'air_temperature' },
  { field: 'humidity_pct', name: 'Humidity', sensorType: 'humidity', measurementType: 'humidity', unit: '%', rawKey: 'humidity' },
] as const

type ArchivedField = typeof FIELD_SPECS[number]['field']

/** pH and TDS are deliberately excluded until server-verified calibration. */
function usableValue(packet: Esp32SensorPacket, field: ArchivedField): number | null {
  const spec = FIELD_SPECS.find(item => item.field === field)
  if (!spec) return null
  const value = packet[field]
  if (value === null || !Number.isFinite(value)) return null
  const diagnostic = packet.raw_readings?.[spec.rawKey as keyof Esp32RawReadings]
  if (diagnostic && diagnostic.status !== 'ok') return null
  return value
}

export function archiveSensorId(systemId: string, field: ArchivedField): string {
  return `${ESP32_ARCHIVE_PREFIX}${systemId}:${field}`
}

export function parseArchiveSensorId(id: string): {
  systemId: string
  field: ArchivedField
} | null {
  if (!id.startsWith(ESP32_ARCHIVE_PREFIX)) return null
  const parts = id.slice(ESP32_ARCHIVE_PREFIX.length).split(':')
  if (parts.length !== 2) return null
  const [systemId, requestedField] = parts
  const spec = FIELD_SPECS.find(item => item.field === requestedField)
  if (!systemId || !spec) return null
  return { systemId, field: spec.field }
}

export function archivedTrendReadings(
  packets: Esp32Telemetry[],
  sensorId: string,
): DashboardSensorReading[] {
  const requested = parseArchiveSensorId(sensorId)
  if (!requested) return []
  return packets.flatMap(item => {
    if (item.system_id !== requested.systemId) return []
    const value = usableValue(item.packet, requested.field)
    if (value === null || !Number.isFinite(Date.parse(item.received_at))) return []
    const spec = FIELD_SPECS.find(candidate => candidate.field === requested.field)!
    return [{
      id: `${sensorId}:${item.id}`,
      sensor_id: sensorId,
      recorded_at: item.received_at,
      value_numeric: value,
      unit: spec.unit,
      quality_status: 'good',
      source: 'hardware',
      sequence_number: item.packet.sequence,
      created_at: item.received_at,
    }]
  })
}

/**
 * Readings are taken from the *newest packet* only, so a disconnected/failed
 * latest probe never gets silently replaced with an older good raw value.
 * Even old saved packets can produce a card: UI freshness checks mark it Late.
 */
export function mergeDashboardEsp32Archive(
  overview: SystemDashboardOverview,
  packets: Esp32Telemetry[],
  systemId: string,
): SystemDashboardOverview {
  const sensors = [...overview.sensors]
  const latestReadings = [...overview.latestReadings]
  const latest = [...packets].filter(item =>
    item.system_id === systemId && Number.isFinite(Date.parse(item.received_at)),
  ).sort((a, b) => Date.parse(b.received_at) - Date.parse(a.received_at))[0]
  if (!latest) return { ...overview, sensors, latestReadings }

  for (const spec of FIELD_SPECS) {
    const value = usableValue(latest.packet, spec.field)
    if (value === null) continue

    const expectedHardwareId = `${latest.packet.device_id}:${spec.field}`
    const registered = sensors.find(sensor => sensor.hardware_identifier === expectedHardwareId)
    // If a registered record explicitly claims this field but is disabled,
    // simulated, or mismatched, do not override it with an archive fallback.
    if (registered && (
      !registered.is_enabled || registered.is_simulated ||
      registered.sensor_type !== spec.sensorType ||
      registered.measurement_type !== spec.measurementType ||
      registered.unit !== spec.unit
    )) continue

    const sensorId = registered?.id ?? archiveSensorId(systemId, spec.field)
    const existingReading = latestReadings.find(reading => reading.sensor_id === sensorId)
    if (existingReading && Date.parse(existingReading.recorded_at) >= Date.parse(latest.received_at)) {
      continue
    }

    if (!registered) {
      const sensor: DashboardSensor = {
        id: sensorId,
        system_id: systemId,
        name: spec.name,
        sensor_type: spec.sensorType,
        measurement_type: spec.measurementType,
        location_type: 'system',
        location_id: null,
        unit: spec.unit,
        hardware_identifier: null,
        is_simulated: false,
        is_enabled: true,
        sampling_interval_seconds: 30,
        calibration_status: 'pending',
        created_at: latest.received_at,
        updated_at: latest.received_at,
      }
      sensors.push(sensor)
    }

    const archivedReading: DashboardSensorReading = {
      id: `${sensorId}:${latest.id}`,
      sensor_id: sensorId,
      recorded_at: latest.received_at,
      value_numeric: value,
      unit: spec.unit,
      quality_status: 'good',
      source: 'hardware',
      sequence_number: latest.packet.sequence,
      created_at: latest.received_at,
    }
    if (existingReading) {
      latestReadings.splice(latestReadings.indexOf(existingReading), 1, archivedReading)
    } else {
      latestReadings.push(archivedReading)
    }
  }

  return { ...overview, sensors, latestReadings }
}
