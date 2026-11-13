import { beforeEach, expect, it, vi } from 'vitest'
import { apiRequest } from './apiClient'
import { listSensorCalibrationRecords } from './sensorCalibrationService'

vi.mock('./apiClient', () => ({ apiRequest: vi.fn() }))

beforeEach(() => vi.resetAllMocks())

it('loads only calibration records for the requested sensor ID', async () => {
  vi.mocked(apiRequest).mockResolvedValueOnce([])
  expect(await listSensorCalibrationRecords('sensor/id')).toEqual([])
  expect(apiRequest).toHaveBeenCalledExactlyOnceWith(
    'sensor-calibrations?sensor_id=sensor%2Fid',
  )
})

it('propagates failures rather than silently inventing verified calibration', async () => {
  const failure = new Error('Backend unavailable')
  vi.mocked(apiRequest).mockRejectedValueOnce(failure)
  await expect(listSensorCalibrationRecords('s')).rejects.toBe(failure)
})
