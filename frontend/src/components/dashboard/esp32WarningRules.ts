import type { Esp32RawReadStatus, Esp32SensorPacket } from '../../types/esp32Telemetry'

export interface Esp32SensorWarning {
  id: string
  title: string
  message: string
  kind: 'threshold' | 'sensor'
}

export const ESP32_WARNING_LIMITS = {
  minimumWaterLevelPct: 75,
  minimumPh: 6.5,
  maximumPh: 7.5,
  maximumTdsPpm: 1000,
} as const

function usable(value: number | null | undefined): value is number {
  return value !== null && value !== undefined && Number.isFinite(value)
}

function fault(status: Esp32RawReadStatus | undefined): boolean {
  return status !== undefined && status !== 'ok' && status !== 'not_configured'
}

/**
 * Advisory, client-side warnings based only on the most recent usable packet.
 * These are not authoritative backend alerts or hardware control decisions.
 */
export function evaluateEsp32Warnings(packet: Esp32SensorPacket): Esp32SensorWarning[] {
  const warnings: Esp32SensorWarning[] = []
  const raw = packet.raw_readings

  for (const sensor of [
    { id: 'ph', title: 'pH probe', status: raw?.ph?.status },
    { id: 'tds', title: 'TDS probe', status: raw?.tds?.status },
    { id: 'ultrasonic', title: 'Water-level sensor', status: raw?.ultrasonic?.status },
    { id: 'water_temperature', title: 'Water temperature sensor', status: raw?.water_temperature?.status },
  ]) {
    if (fault(sensor.status)) {
      warnings.push({
        id: `fault-${sensor.id}`,
        title: `${sensor.title} needs attention`,
        message: `ESP32 reported ${sensor.status?.replaceAll('_', ' ')}. Check wiring and sensor status; no reliable reading is assumed.`,
        kind: 'sensor',
      })
    }
  }

  if (!fault(raw?.ultrasonic?.status) && usable(packet.water_level_pct) &&
      packet.water_level_pct < ESP32_WARNING_LIMITS.minimumWaterLevelPct) {
    warnings.push({
      id: 'water-level-low',
      title: 'Water level below 75%',
      message: `Latest water level: ${packet.water_level_pct.toFixed(1)}%. Check the system's water supply.`,
      kind: 'threshold',
    })
  }

  if (packet.ph_calibrated && !fault(raw?.ph?.status) && usable(packet.ph) &&
      (packet.ph < ESP32_WARNING_LIMITS.minimumPh || packet.ph > ESP32_WARNING_LIMITS.maximumPh)) {
    warnings.push({
      id: 'ph-out-of-range',
      title: 'pH outside monitoring range',
      message: `Device-reported pH: ${packet.ph.toFixed(2)}. Advisory range: 6.5–7.5; verify probe calibration before adjusting water chemistry.`,
      kind: 'threshold',
    })
  }

  if (packet.tds_calibrated && !fault(raw?.tds?.status) && usable(packet.tds_ppm) &&
      packet.tds_ppm > ESP32_WARNING_LIMITS.maximumTdsPpm) {
    warnings.push({
      id: 'tds-high',
      title: 'TDS above 1,000 ppm',
      message: `Device-reported TDS: ${Math.round(packet.tds_ppm).toLocaleString('en-US')} ppm. Verify calibration and investigate elevated dissolved solids.`,
      kind: 'threshold',
    })
  }

  return warnings
}

/** Missing or stale packets must not be presented as current threshold alerts. */
export function isFreshEsp32Packet(receivedAt: string, nowMs: number): boolean {
  const receivedMs = Date.parse(receivedAt)
  return Number.isFinite(receivedMs) && receivedMs <= nowMs + 5000 &&
    nowMs - receivedMs <= 45000
}
