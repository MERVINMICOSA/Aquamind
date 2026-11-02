import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { listEsp32Telemetry } from '../../services/esp32TelemetryService'
import { Esp32TelemetryPanel } from './Esp32TelemetryPanel'

vi.mock('../../services/esp32TelemetryService', () => ({
  listEsp32Telemetry: vi.fn(),
}))

const packet = {
  type: 'aquamind_sensor' as const,
  schema_version: 1 as const,
  device_id: 'esp32-devkit-01',
  sequence: 5,
  uptime_ms: 15023,
  water_temp_c: 27.56,
  ph_voltage_v: 0.559,
  ph_unverified_estimate: 17.45,
  ph_calibrated: false,
  ph: null,
  tds_voltage_v: 2.435,
  tds_unverified_ppm: 1249,
  tds_calibrated: false,
  tds_ppm: null,
  distance_cm: null,
  water_height_cm: null,
  water_level_pct: null,
  air_temp_c: 27.67,
  humidity_pct: 84.60,
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('ESP32 telemetry dashboard panel', () => {
  it('displays a saved ESP32 record without promoting unverified estimates', async () => {
    vi.mocked(listEsp32Telemetry).mockResolvedValue([{
      id: 'row-1', system_id: 'system-1',
      received_at: '2026-11-03T00:00:00Z',
      packet,
    }])

    render(<Esp32TelemetryPanel systemId="system-1" />)

    expect(await screen.findByText('27.56 °C')).toBeInTheDocument()
    expect(screen.getAllByText('Not calibrated')).toHaveLength(2)
    expect(screen.getByText(/17\.45 \(not a valid calibrated pH reading\)/)).toBeInTheDocument()
    expect(screen.getByText(/1249 ppm \(not calibrated\)/)).toBeInTheDocument()
    expect(screen.getAllByText('No reading').length).toBeGreaterThanOrEqual(3)
    expect(screen.getByRole('columnheader', { name: 'Sequence' })).toBeInTheDocument()
    expect(listEsp32Telemetry).toHaveBeenCalledWith('system-1')
  })

  it('shows no records when the database contains no packets', async () => {
    vi.mocked(listEsp32Telemetry).mockResolvedValue([])
    render(<Esp32TelemetryPanel systemId="system-1" />)
    expect(await screen.findByText(/No ESP32 packets saved/)).toBeInTheDocument()
  })
})
