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
  vi.restoreAllMocks()
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

  it('shows device-reported raw values and faults, including real zero counts', async () => {
    vi.mocked(listEsp32Telemetry).mockResolvedValue([{
      id: 'row-raw', system_id: 'system-1',
      received_at: '2026-11-03T00:00:00Z',
      packet: {
        ...packet,
        raw_readings: {
          ph: { status: 'ok', value: 0, unit: 'adc_count' },
          tds: { status: 'ok', value: 2145, unit: 'adc_count' },
          ultrasonic: { status: 'timeout', value: null, unit: 'microseconds', error_code: 'echo_timeout' },
          water_temperature: { status: 'disconnected', error_code: 'ds18b20_disconnected' },
        },
      },
    }])

    render(<Esp32TelemetryPanel systemId="system-1" />)
    expect(await screen.findByText('Raw USB readings and sensor status')).toBeInTheDocument()
    expect(screen.getAllByText('0 ADC counts').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('2145 ADC counts').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('echo_timeout')).toBeInTheDocument()
    expect(screen.getByText('ds18b20_disconnected')).toBeInTheDocument()
    expect(screen.getByText('Disconnected')).toBeInTheDocument()
    expect(screen.getAllByText('Timeout').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Not reported').length).toBeGreaterThanOrEqual(1)
  })

  it('hides the obsolete water probes even when old packets contain them', async () => {
    vi.mocked(listEsp32Telemetry).mockResolvedValue([{
      id: 'row-water', system_id: 'system-1',
      received_at: '2026-11-03T00:00:00Z',
      packet: {
        ...packet,
        reservoir_water_present: null,
        raft2_water_present: null,
        raw_readings: {
          reservoir_level: { status: 'ok', value: 0, unit: 'adc_count' },
          raft2_level: { status: 'ok', value: 1800, unit: 'adc_count' },
        },
      },
    }])
    render(<Esp32TelemetryPanel systemId="system-1" />)
    expect(await screen.findByText('Raw USB readings and sensor status')).toBeInTheDocument()
    expect(screen.queryByText('Reservoir water')).not.toBeInTheDocument()
    expect(screen.queryByText('Second raft water')).not.toBeInTheDocument()
    expect(screen.queryByText('Reservoir presence probe')).not.toBeInTheDocument()
    expect(screen.queryByText('Second raft presence probe')).not.toBeInTheDocument()
  })

  it('renders sample USB and water-probe diagnostics without polling the API', async () => {
    const samplePacket = {
      ...packet,
      device_id: 'demo-esp32-not-connected',
      reservoir_water_present: null,
      raft2_water_present: null,
      raw_readings: {
        reservoir_level: { status: 'ok' as const, value: 1820, unit: 'adc_count' as const },
        raft2_level: { status: 'ok' as const, value: 1900, unit: 'adc_count' as const },
      },
    }
    render(<Esp32TelemetryPanel
      systemId="demo"
      demoPackets={[{
        id: 'demo-row',
        system_id: 'demo',
        received_at: '2026-11-03T00:00:00Z',
        packet: samplePacket,
      }]}
    />)

    expect(screen.getAllByText('demo-esp32-not-connected').length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText('1820 ADC counts')).not.toBeInTheDocument()
    expect(screen.queryByText('1900 ADC counts')).not.toBeInTheDocument()
    expect(listEsp32Telemetry).not.toHaveBeenCalled()
  })

  it.each([
    ['Connected', '2026-11-03T00:00:58Z'],
    ['No recent data', '2026-11-03T00:00:30Z'],
    ['Disconnected', '2026-11-03T00:00:00Z'],
  ])('shows %s based on the newest saved packet timestamp', async (label, received_at) => {
    vi.spyOn(Date, 'now').mockReturnValue(Date.parse('2026-11-03T00:01:00Z'))
    vi.mocked(listEsp32Telemetry).mockResolvedValue([{
      id: 'row-status', system_id: 'system-1', received_at, packet,
    }])
    render(<Esp32TelemetryPanel systemId="system-1" />)
    expect(await screen.findByText(`ESP32: ${label}`)).toBeInTheDocument()
  })

  it('shows no records when the database contains no packets', async () => {
    vi.mocked(listEsp32Telemetry).mockResolvedValue([])
    render(<Esp32TelemetryPanel systemId="system-1" />)
    expect(await screen.findByText(/No ESP32 packets saved/)).toBeInTheDocument()
  })
})
