import { apiRequest } from './apiClient'
import type { Esp32Telemetry } from '../types/esp32Telemetry'

/**
 * Read persisted ESP32 packet history using the signed-in admin session.
 * Never place the device ingestion token in frontend JavaScript.
 */
export function listEsp32Telemetry(
  systemId: string,
  limit = 10,
): Promise<Esp32Telemetry[]> {
  const boundedLimit = Math.max(1, Math.min(100, Math.trunc(limit)))
  return apiRequest<Esp32Telemetry[]>(
    `esp32/telemetry?system_id=${encodeURIComponent(systemId)}&limit=${boundedLimit}`,
  )
}


export type Esp32HistoryField =
  | 'all'
  | 'water_temp_c'
  | 'ph'
  | 'tds_ppm'
  | 'water_level_pct'
  | 'water_height_cm'
  | 'distance_cm'
  | 'air_temp_c'
  | 'humidity_pct'

export interface Esp32HistorySearchFilters {
  systemId: string
  field: Esp32HistoryField
  startAt?: string
  endAt?: string
  offset?: number
  limit?: number
}

export interface Esp32HistorySearchResult {
  items: Esp32Telemetry[]
  total: number
  offset: number
  limit: number
}

/** Query historical measurements in PostgreSQL, not only the latest packets. */
export function searchEsp32Telemetry(
  filters: Esp32HistorySearchFilters,
): Promise<Esp32HistorySearchResult> {
  const params = new URLSearchParams({
    system_id: filters.systemId,
    field: filters.field,
    offset: String(Math.max(0, Math.trunc(filters.offset ?? 0))),
    limit: String(Math.max(1, Math.min(100, Math.trunc(filters.limit ?? 25)))),
  })
  if (filters.startAt) params.set('start_at', filters.startAt)
  if (filters.endAt) params.set('end_at', filters.endAt)
  return apiRequest<Esp32HistorySearchResult>(
    `esp32/telemetry/search?${params.toString()}`,
  )
}


/** Most recent USB packet, independent of how often history is saved. */
export function getLatestEsp32Telemetry(systemId: string): Promise<Esp32Telemetry | null> {
  return apiRequest<Esp32Telemetry | null>(
    `esp32/telemetry/latest?system_id=${encodeURIComponent(systemId)}`,
  )
}

export type Esp32CaptureMode = 'live' | 'timed'

export interface Esp32CaptureSettings {
  system_id: string
  device_id: string | null
  mode: Esp32CaptureMode
  interval_minutes: number
  latest_received_at: string | null
  last_saved_at: string | null
  last_saved_scheduled_at: string | null
  next_save_at: string | null
}

export function getEsp32CaptureSettings(systemId: string): Promise<Esp32CaptureSettings> {
  return apiRequest<Esp32CaptureSettings>(
    `esp32/capture?system_id=${encodeURIComponent(systemId)}`,
  )
}

export function updateEsp32CaptureSettings(
  systemId: string,
  mode: Esp32CaptureMode,
  intervalMinutes: number,
): Promise<Esp32CaptureSettings> {
  return apiRequest<Esp32CaptureSettings>(
    `esp32/capture?system_id=${encodeURIComponent(systemId)}`,
    {
      method: 'PUT',
      body: JSON.stringify({ mode, interval_minutes: intervalMinutes }),
    },
  )
}

export function addEsp32Correction(
  systemId: string, telemetryId: string,
  field: Exclude<Esp32HistoryField, 'all'>, value: number, reason: string,
): Promise<Esp32Telemetry> {
  return apiRequest<Esp32Telemetry>(
    `esp32/telemetry/${encodeURIComponent(telemetryId)}/corrections?system_id=${encodeURIComponent(systemId)}`,
    { method: 'POST', body: JSON.stringify({ field, value, reason }) },
  )
}
