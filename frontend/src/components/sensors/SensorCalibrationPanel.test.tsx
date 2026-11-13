import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { SensorCalibrationPanel } from './SensorCalibrationPanel'
import { listSensorCalibrationRecords } from '../../services/sensorCalibrationService'

vi.mock('../../services/sensorCalibrationService', () => ({
  listSensorCalibrationRecords: vi.fn(),
}))

const calibration = {
  id: 'cal-1',
  sensor_id: 'sensor-1',
  offset: -0.02,
  factor: 1.01,
  calibration_data: null,
  performed_at: '2026-11-09T08:00:00Z',
  verified_by_user_id: 'user-1',
  status: 'verified' as const,
  notes: 'Three buffer calibration',
  created_at: '2026-11-09T08:00:01Z',
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listSensorCalibrationRecords).mockResolvedValue([])
})

it('reports missing calibration records without claiming sensor calibration', async () => {
  render(<SensorCalibrationPanel
    sensorId="sensor-1"
    sensorType="ph"
    calibrationStatus="pending"
  />)
  expect(await screen.findByText('No calibration records were returned for this sensor.'))
    .toBeInTheDocument()
  expect(screen.getByText(/is not marked as verified/)).toBeInTheDocument()
  expect(screen.getByText(/saving a record does not/)).toBeDefined()
})

it('shows only the selected sensor calibration history and does not change firmware', async () => {
  vi.mocked(listSensorCalibrationRecords).mockResolvedValue([
    calibration,
    { ...calibration, id: 'other', sensor_id: 'sensor-2' },
  ])
  render(<SensorCalibrationPanel
    sensorId="sensor-1"
    sensorType="ph"
    calibrationStatus="verified"
  />)
  const table = await screen.findByRole('table', { name: 'Sensor calibration history' })
  expect(table).toHaveTextContent('Three buffer calibration')
  expect(table).toHaveTextContent('verified')
  expect(table).not.toHaveTextContent('other')
  expect(listSensorCalibrationRecords).toHaveBeenCalledWith('sensor-1')
  expect(screen.getByText(/saving a record does not/)).toHaveTextContent(/does not/)
})

it('flags mismatch between registered verified status and latest calibration record', async () => {
  vi.mocked(listSensorCalibrationRecords).mockResolvedValue([
    { ...calibration, status: 'expired' },
  ])
  render(<SensorCalibrationPanel
    sensorId="sensor-1"
    sensorType="ph"
    calibrationStatus="verified"
  />)
  expect(await screen.findByRole('alert'))
    .toHaveTextContent('newest calibration record is expired')
})

it('shows a load error instead of assuming calibration passed', async () => {
  vi.mocked(listSensorCalibrationRecords).mockRejectedValue(new Error('Unavailable'))
  render(<SensorCalibrationPanel
    sensorId="sensor-1"
    sensorType="tds"
    calibrationStatus="pending"
  />)
  await waitFor(() => expect(screen.getByRole('alert'))
    .toHaveTextContent('Unable to load calibration records'))
})
