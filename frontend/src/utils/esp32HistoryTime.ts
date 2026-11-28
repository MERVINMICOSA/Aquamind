import type { Esp32Telemetry } from '../types/esp32Telemetry'

export function historyTime(item: Esp32Telemetry): string {
  return item.validation_at ?? item.received_at
}

export function formatPhilippineTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleString(undefined, { timeZone: 'Asia/Manila' })
}

export function philippineDayStart(day: string): string | undefined {
  if (!day) return undefined
  const date = new Date(`${day}T00:00:00+08:00`)
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString()
}

export function philippineDayEnd(day: string): string | undefined {
  const start = philippineDayStart(day)
  return start ? new Date(Date.parse(start) + 86400000).toISOString() : undefined
}

export function philippineIso(value: string): string {
  const ms = Date.parse(value)
  if (!Number.isFinite(ms)) return ''
  return new Date(ms + 8 * 3600000).toISOString().replace(/Z$/, '+08:00')
}

/** Imported schedule metadata, plus the legacy import identifier for older backups. */
export function isImportedHistory(item: Esp32Telemetry): boolean {
  return item.validation_at != null || item.packet.device_id === 'test-esp32-devkit-01'
}
