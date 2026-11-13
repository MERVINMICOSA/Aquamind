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
  minValue?: number
  maxValue?: number
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
  if (filters.minValue !== undefined) params.set('min_value', String(filters.minValue))
  if (filters.maxValue !== undefined) params.set('max_value', String(filters.maxValue))
  return apiRequest<Esp32HistorySearchResult>(
    `esp32/telemetry/search?${params.toString()}`,
  )
}
