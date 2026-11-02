import { describe, expect, it, vi } from 'vitest'
import { apiRequest } from './apiClient'
import { listEsp32Telemetry } from './esp32TelemetryService'

vi.mock('./apiClient', () => ({ apiRequest: vi.fn() }))

describe('ESP32 telemetry API', () => {
  it('requests bounded history scoped to the selected system', async () => {
    vi.mocked(apiRequest).mockResolvedValue([])
    await listEsp32Telemetry('system / one')
    expect(apiRequest).toHaveBeenCalledWith(
      'esp32/telemetry?system_id=system%20%2F%20one&limit=10',
    )
  })
})
