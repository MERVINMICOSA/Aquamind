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
