import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSensorsOverview } from '../hooks/useSensorsOverview'
import { SensorsPage } from './SensorsPage'

vi.mock('../hooks/useSensorsOverview', () => ({
  useSensorsOverview: vi.fn(),
}))

vi.mock('../components/dashboard/Esp32TelemetryPanel', () => ({
  Esp32TelemetryPanel: ({
    systemId, mode,
  }: { systemId: string; mode?: string }) => (
    <div data-testid="live-sensors">System {systemId} ({mode})</div>
  ),
}))

const system = {
  id: 'system-1', name: 'AquaMind Tank', description: null,
  timezone: 'UTC', is_active: true,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('simplified Sensors page', () => {
  it('shows just the current-reading panel without identifier configuration', () => {
    vi.mocked(useSensorsOverview).mockReturnValue({
      systems: [system],
      selectedSystem: system,
      selectedSystemId: system.id,
      selectSystem: vi.fn(),
      sensors: [],
      latestReadings: [],
      systemsStatus: 'ready',
      sensorsStatus: 'ready',
      errorMessage: null,
    })

    render(<MemoryRouter><SensorsPage /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Sensors' })).toBeInTheDocument()
    expect(screen.getByTestId('live-sensors')).toHaveTextContent('system-1 (simple)')
    expect(screen.getByText(/Only sensors with current/)).toBeInTheDocument()
    expect(screen.queryByText('Hardware identifier')).not.toBeInTheDocument()
    expect(screen.queryByText('Location ID')).not.toBeInTheDocument()
    expect(screen.queryByText('No sensors configured')).not.toBeInTheDocument()
  })

  it('gives a clear empty state when there is no aquaponics system', () => {
    vi.mocked(useSensorsOverview).mockReturnValue({
      systems: [], selectedSystem: null, selectedSystemId: null,
      selectSystem: vi.fn(), sensors: [], latestReadings: [],
      systemsStatus: 'ready', sensorsStatus: 'idle', errorMessage: null,
    })
    render(<MemoryRouter><SensorsPage /></MemoryRouter>)
    expect(screen.getByRole('heading', {
      name: 'No aquaponics system configured',
    })).toBeInTheDocument()
    expect(screen.queryByTestId('live-sensors')).not.toBeInTheDocument()
  })
})
