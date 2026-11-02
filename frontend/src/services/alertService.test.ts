import { beforeEach, expect, it, vi } from 'vitest'
import { apiRequest } from './apiClient'
import { loadAlertHistoryPage } from './alertService'

vi.mock('./apiClient', () => ({ apiRequest: vi.fn() }))
beforeEach(() => vi.resetAllMocks())

it.each([0, 50, 51])('preserves server order and uses lookahead with %i results', async count => {
  const alerts = Array.from({ length: count }, (_, index) => ({ id: `alert-${count - index}` }))
  vi.mocked(apiRequest).mockResolvedValueOnce(alerts)
  expect(await loadAlertHistoryPage('system/1', 50)).toEqual({
    alerts: alerts.slice(0, 50), hasNext: count > 50, hasPrevious: true, offset: 50,
  })
  expect(apiRequest).toHaveBeenCalledExactlyOnceWith('alerts/history?system_id=system%2F1&limit=51&offset=50')
})

it.each([[-3, 0], [0, 0], [50.9, 50]])('normalizes offset %s to %s', async (offset, expected) => {
  vi.mocked(apiRequest).mockResolvedValueOnce([])
  const result = await loadAlertHistoryPage('s', offset)
  expect(apiRequest).toHaveBeenCalledExactlyOnceWith(`alerts/history?system_id=s&limit=51&offset=${expected}`)
  expect(result.offset).toBe(expected)
  expect(result.hasPrevious).toBe(expected > 0)
})

it('propagates request errors instead of reporting empty history', async () => {
  const error = new Error('Unavailable')
  vi.mocked(apiRequest).mockRejectedValueOnce(error)
  await expect(loadAlertHistoryPage('s', 0)).rejects.toBe(error)
})
