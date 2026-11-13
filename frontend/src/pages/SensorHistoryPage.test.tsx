import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listSystems } from '../services/dashboardService'
import { searchEsp32Telemetry } from '../services/esp32TelemetryService'
import { SensorHistoryPage } from './SensorHistoryPage'

vi.mock('../services/dashboardService', () => ({
  listSystems: vi.fn(),
}))
vi.mock('../services/esp32TelemetryService', () => ({
  searchEsp32Telemetry: vi.fn(),
}))
vi.mock('../components/sensors/SensorTrendChart', () => ({
  SensorTrendChart: ({ readings }: { readings: unknown[] }) => (
    <div data-testid="history-chart">{readings.length} chart points</div>
  ),
}))

const SYSTEM = {
  id: 'system-one',
  name: 'Tilapia and lettuce system',
  description: null,
  timezone: 'Asia/Manila',
  is_active: true,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
}

const ITEM = {
  id: 'record-1',
  system_id: SYSTEM.id,
  received_at: '2026-11-13T12:30:00Z',
  packet: {
    type: 'aquamind_sensor' as const,
    schema_version: 1 as const,
    device_id: 'esp32-devkit-01',
    sequence: 10,
    uptime_ms: 32100,
    water_temp_c: 27.56,
    ph_voltage_v: 0.5,
    ph_unverified_estimate: 17.45,
    ph_calibrated: false,
    ph: null,
    tds_voltage_v: 2.4,
    tds_unverified_ppm: 1249,
    tds_calibrated: false,
    tds_ppm: null,
    distance_cm: null,
    water_height_cm: null,
    water_level_pct: null,
    air_temp_c: 27.67,
    humidity_pct: 84.6,
  },
}

function mount() {
  return render(<MemoryRouter><SensorHistoryPage /></MemoryRouter>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(listSystems).mockResolvedValue([SYSTEM])
  vi.mocked(searchEsp32Telemetry).mockResolvedValue({
    items: [ITEM], total: 1, limit: 25, offset: 0,
  })
})

describe('searchable ESP32 history', () => {
  it('loads archived measurements with a trend and no internal device IDs', async () => {
    mount()
    expect(await screen.findByText('27.56 °C')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sensor History' })).toBeInTheDocument()
    expect(screen.getByTestId('history-chart')).toHaveTextContent('1 chart points')
    expect(screen.getByText(/1 matching saved readings/)).toBeInTheDocument()
    expect(screen.queryByText('esp32-devkit-01')).not.toBeInTheDocument()
    expect(vi.mocked(searchEsp32Telemetry)).toHaveBeenCalledWith(
      expect.objectContaining({
        systemId: SYSTEM.id, field: 'water_temp_c',
        limit: 25, offset: 0,
      }),
    )
  })

  it('searches selected field, dates and numeric ranges on the backend', async () => {
    mount()
    await screen.findByText('27.56 °C')
    const user = userEvent.setup()
    await user.selectOptions(screen.getByLabelText('Sensor'), 'humidity_pct')
    fireEvent.change(screen.getByLabelText('From date'), {
      target: { value: '2026-11-01' },
    })
    fireEvent.change(screen.getByLabelText('To date'), {
      target: { value: '2026-11-14' },
    })
    await user.type(screen.getByLabelText('Minimum value'), '70')
    await user.type(screen.getByLabelText('Maximum value'), '90')
    await user.click(screen.getByRole('button', { name: 'Search readings' }))

    await waitFor(() => {
      expect(vi.mocked(searchEsp32Telemetry)).toHaveBeenLastCalledWith(
        expect.objectContaining({
          field: 'humidity_pct', minValue: 70, maxValue: 90,
          limit: 25, offset: 0,
          startAt: expect.any(String),
          endAt: expect.any(String),
        }),
      )
    })
    expect(await screen.findByText('84.60 %')).toBeInTheDocument()
  })

  it('rejects reversed date filters before making a search request', async () => {
    mount()
    await screen.findByText('27.56 °C')
    fireEvent.change(screen.getByLabelText('From date'), {
      target: { value: '2026-11-15' },
    })
    fireEvent.change(screen.getByLabelText('To date'), {
      target: { value: '2026-11-14' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Search readings' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Start date cannot be after end date')
    expect(searchEsp32Telemetry).toHaveBeenCalledTimes(1)
  })

  it('pages through all saved matching records', async () => {
    vi.mocked(searchEsp32Telemetry).mockResolvedValue({
      items: [ITEM], total: 52, limit: 25, offset: 0,
    })
    mount()
    await screen.findByText('27.56 °C')
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await waitFor(() => {
      expect(searchEsp32Telemetry).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 25, limit: 25 }),
      )
    })
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
  })

  it('labels pH history as unverified device-reported diagnostic data', async () => {
    vi.mocked(searchEsp32Telemetry).mockResolvedValue({
      items: [{
        ...ITEM,
        packet: { ...ITEM.packet, ph_calibrated: true, ph: 7.1 },
      }], total: 1, limit: 25, offset: 0,
    })
    mount()
    await screen.findByText('27.56 °C')
    const user = userEvent.setup()
    await user.selectOptions(screen.getByLabelText('Sensor'), 'ph')
    await user.click(screen.getByRole('button', { name: 'Search readings' }))
    expect(await screen.findByText('7.10 pH')).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent('not independently verified')
    expect(screen.getByText('Device reported — not independently verified')).toBeInTheDocument()
  })

  it('renders an honest empty state when a search has no saved matches', async () => {
    vi.mocked(searchEsp32Telemetry).mockResolvedValue({
      items: [], total: 0, limit: 25, offset: 0,
    })
    mount()
    expect(await screen.findByText('No saved readings match this search.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled()
  })
})
