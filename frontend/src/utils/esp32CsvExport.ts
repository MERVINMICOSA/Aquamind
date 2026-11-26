import type { Esp32Telemetry, Esp32RawReadings } from '../types/esp32Telemetry'
import type { Esp32HistoryField } from '../services/esp32TelemetryService'
import { historyTime, philippineIso } from './esp32HistoryTime'

type Field = Exclude<Esp32HistoryField, 'all'>

const FIELDS: { key: Field; header: string; rawKey: keyof Esp32RawReadings }[] = [
  { key: 'water_temp_c', header: 'Water temperature (C)', rawKey: 'water_temperature' },
  { key: 'air_temp_c', header: 'Air temperature (C)', rawKey: 'air_temperature' },
  { key: 'humidity_pct', header: 'Humidity (%)', rawKey: 'humidity' },
  { key: 'water_level_pct', header: 'Water level (%)', rawKey: 'ultrasonic' },
  { key: 'water_height_cm', header: 'Water height (cm)', rawKey: 'ultrasonic' },
  { key: 'distance_cm', header: 'Ultrasonic distance (cm)', rawKey: 'ultrasonic' },
  { key: 'ph', header: 'pH (device reported)', rawKey: 'ph' },
  { key: 'tds_ppm', header: 'TDS (ppm, device reported)', rawKey: 'tds' },
]

function safeCell(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : ''
  // Prevent spreadsheet formulas embedded in device-provided strings.
  const guarded = /^[\s]*[=+\-@]|^[\t\r\n]/.test(value) ? `'${value}` : value
  return `"${guarded.replaceAll('"', '""')}"`
}

function measurement(item: Esp32Telemetry, field: typeof FIELDS[number]): [number | null, string] {
  const raw = item.packet.raw_readings?.[field.rawKey]
  if (raw && raw.status !== 'ok') {
    return [null, `Sensor read: ${raw.status.replaceAll('_', ' ')}`]
  }
  if (field.key === 'ph' && !item.packet.ph_calibrated) return [null, 'Not calibrated']
  if (field.key === 'tds_ppm' && !item.packet.tds_calibrated) return [null, 'Not calibrated']
  const value = item.packet[field.key]
  if (value === null || !Number.isFinite(value)) return [null, 'No reading']
  return [value, field.key === 'ph' || field.key === 'tds_ppm'
    ? 'Device reported; calibration not independently verified'
    : 'Recorded']
}

/** One CSV row per archived packet, never fabricated for missing measurements. */
export function buildEsp32HistoryCsv(items: Esp32Telemetry[], chosenField: Esp32HistoryField): string {
  const fields = chosenField === 'all'
    ? FIELDS
    : FIELDS.filter(field => field.key === chosenField)

  const header = ['Received at (UTC)', 'Device ID', 'Sequence', 'Uptime (ms)',
    ...fields.flatMap(field => [field.header, `${field.header} status`]), 'Display time (PHT)', 'Data source', 'Manual correction log (JSON)']
  const rows: (string | number | null)[][] = items.map(item => [
    item.received_at,
    item.packet.device_id,
    item.packet.sequence,
    item.packet.uptime_ms,
    ...fields.flatMap(field => measurement(item, field)),
    philippineIso(historyTime(item)),
    item.packet.device_id === 'test-esp32-devkit-01' ? 'Imported validation; original UTC label is not verified receipt' : 'Automatic receipt',
    JSON.stringify(item.correction_log ?? []),
  ])
  return [header, ...rows].map(row => row.map(safeCell).join(',')).join('\r\n') + '\r\n'
}

export function downloadEsp32HistoryCsv(items: Esp32Telemetry[], field: Esp32HistoryField): void {
  const csv = '\uFEFF' + buildEsp32HistoryCsv(items, field)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `aquamind-esp32-${field}-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.append(link)
  try {
    link.click()
  } finally {
    link.remove()
    URL.revokeObjectURL(url)
  }
}
