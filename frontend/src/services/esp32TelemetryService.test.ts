import { describe, expect, it, vi } from 'vitest'
import { apiRequest } from './apiClient'
import { listEsp32Telemetry, searchEsp32Telemetry } from './esp32TelemetryService'

vi.mock('./apiClient', () => ({ apiRequest: vi.fn() }))

describe('ESP32 telemetry API', () => {
  it('encodes All data and date-only history searches as URL parameters', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ items: [], total: 0, offset: 25, limit: 25 })
    await searchEsp32Telemetry({
      systemId: 'system / test',
      field: 'all',
      startAt: '2026-11-12T16:00:00.000Z',
      endAt: '2026-11-14T16:00:00.000Z',
      limit: 25,
      offset: 25,
    })
    const url = vi.mocked(apiRequest).mock.calls.at(-1)?.[0]
    expect(url?.startsWith('esp32/telemetry/search?')).toBe(true)
    const params = new URLSearchParams(url?.split('?')[1])
    expect(params.get('system_id')).toBe('system / test')
    expect(params.get('field')).toBe('all')
    expect(params.get('start_at')).toBe('2026-11-12T16:00:00.000Z')
    expect(params.get('end_at')).toBe('2026-11-14T16:00:00.000Z')
    expect(params.has('min_value')).toBe(false)
    expect(params.has('max_value')).toBe(false)
    expect(params.get('offset')).toBe('25')
  })

  it('requests bounded history scoped to the selected system', async () => {
    vi.mocked(apiRequest).mockResolvedValue([])
    await listEsp32Telemetry('system / one')
    expect(apiRequest).toHaveBeenCalledWith(
      'esp32/telemetry?system_id=system%20%2F%20one&limit=10',
    )
  })
})
