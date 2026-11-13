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

describe('simplified ESP32 history', () => {
  it('defaults to All data and displays all sensor columns without extra filters', async () => {
    mount()
    expect(await screen.findByText('27.56 °C')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sensor History' })).toBeInTheDocument()
    expect(screen.getByLabelText('Sensor')).toHaveValue('all')
    expect(screen.getByRole('columnheader', { name: 'Water temperature' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Air temperature' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Humidity' })).toBeInTheDocument()
    expect(screen.getByText('84.60 %')).toBeInTheDocument()
    expect(screen.getAllByText('Not calibrated')).toHaveLength(2)
    expect(screen.getByText(/1 matching saved packets/)).toBeInTheDocument()
    expect(screen.getByText(/Showing history for/)).toHaveTextContent(SYSTEM.name)
    expect(screen.queryByLabelText('Aquaponics system')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Minimum value')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Maximum value')).not.toBeInTheDocument()
    expect(screen.queryByTestId('history-chart')).not.toBeInTheDocument()
    expect(screen.queryByText('esp32-devkit-01')).not.toBeInTheDocument()
    expect(searchEsp32Telemetry).toHaveBeenCalledWith(
      expect.objectContaining({
        systemId: SYSTEM.id, field: 'all', limit: 25, offset: 0,
      }),
    )
  })

  it('uses the active system automatically even when it is not first', async () => {
    vi.mocked(listSystems).mockResolvedValue([
      { ...SYSTEM, id: 'old-system', name: 'Inactive', is_active: false },
      SYSTEM,
    ])
    mount()
    expect(await screen.findByText('27.56 °C')).toBeInTheDocument()
    expect(searchEsp32Telemetry).toHaveBeenCalledWith(
      expect.objectContaining({ systemId: SYSTEM.id }),
    )
    expect(screen.queryByRole('combobox', { name: 'Aquaponics system' }))
      .not.toBeInTheDocument()
  })

  it('still shows an individual sensor chart and date-range filtering', async () => {
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
    await user.click(screen.getByRole('button', { name: 'Search readings' }))

    await waitFor(() => {
      expect(searchEsp32Telemetry).toHaveBeenLastCalledWith(
        expect.objectContaining({
          field: 'humidity_pct', limit: 25, offset: 0,
          startAt: expect.any(String), endAt: expect.any(String),
        }),
      )
    })
    expect(await screen.findByText('84.60 %')).toBeInTheDocument()
    expect(screen.getByTestId('history-chart')).toHaveTextContent('1 chart points')
  })

  it('rejects reversed date filters without sending a new request', async () => {
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

  it('pages through all saved packets rather than individual sensor columns', async () => {
    vi.mocked(searchEsp32Telemetry).mockResolvedValue({
      items: [ITEM], total: 52, limit: 25, offset: 0,
    })
    mount()
    await screen.findByText('27.56 °C')
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await waitFor(() => {
      expect(searchEsp32Telemetry).toHaveBeenCalledWith(
        expect.objectContaining({ field: 'all', offset: 25, limit: 25 }),
      )
    })
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
  })

  it('clears date filters and returns to All data', async () => {
    mount()
    await screen.findByText('27.56 °C')
    const user = userEvent.setup()
    await user.selectOptions(screen.getByLabelText('Sensor'), 'air_temp_c')
    fireEvent.change(screen.getByLabelText('From date'), {
      target: { value: '2026-11-01' },
    })
    await user.click(screen.getByRole('button', { name: 'Search readings' }))
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    await waitFor(() => {
      expect(screen.getByLabelText('Sensor')).toHaveValue('all')
      expect(screen.getByLabelText('From date')).toHaveValue('')
      expect(searchEsp32Telemetry).toHaveBeenLastCalledWith(
        expect.objectContaining({ field: 'all' }),
      )
    })
  })

  it('marks device-reported pH as unverified in the combined table', async () => {
    vi.mocked(searchEsp32Telemetry).mockResolvedValue({
      items: [{ ...ITEM, packet: { ...ITEM.packet, ph_calibrated: true, ph: 7.1 } }],
      total: 1, limit: 25, offset: 0,
    })
    mount()
    expect(await screen.findByText('7.10 pH')).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent('not independently')
    expect(screen.getByRole('columnheader', { name: 'pH (device reported)' }))
      .toBeInTheDocument()
  })

  it('shows read faults in the combined view, without inventing readings', async () => {
    vi.mocked(searchEsp32Telemetry).mockResolvedValue({
      items: [{
        ...ITEM,
        packet: {
          ...ITEM.packet,
          raw_readings: {
            water_temperature: {
              status: 'disconnected' as const, error_code: 'sensor_missing',
            },
          },
        },
      }], total: 1, limit: 25, offset: 0,
    })
    mount()
    expect(await screen.findByText('Sensor read: disconnected')).toBeInTheDocument()
    expect(screen.queryByText('27.56 °C')).not.toBeInTheDocument()
  })

  it('renders an honest empty state when no matching saved packets exist', async () => {
    vi.mocked(searchEsp32Telemetry).mockResolvedValue({
      items: [], total: 0, limit: 25, offset: 0,
    })
    mount()
    expect(await screen.findByText('No saved readings match this search.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled()
  })
})
