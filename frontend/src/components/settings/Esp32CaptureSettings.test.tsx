import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  getEsp32CaptureSettings,
  updateEsp32CaptureSettings,
} from '../../services/esp32TelemetryService'
import { Esp32CaptureSettings } from './Esp32CaptureSettings'

vi.mock('../../services/esp32TelemetryService', () => ({
  getEsp32CaptureSettings: vi.fn(),
  updateEsp32CaptureSettings: vi.fn(),
}))

const initial = {
  system_id: 'system-1',
  device_id: 'esp32-devkit-01',
  mode: 'live' as const,
  interval_minutes: 5,
  latest_received_at: '2026-11-22T10:00:00Z',
  last_saved_at: '2026-11-22T10:00:00Z',
  last_saved_scheduled_at: null,
  next_save_at: null,
}

beforeEach(() => {
  vi.mocked(getEsp32CaptureSettings).mockReset()
  vi.mocked(updateEsp32CaptureSettings).mockReset()
  vi.mocked(getEsp32CaptureSettings).mockResolvedValue(initial)
  vi.mocked(updateEsp32CaptureSettings).mockImplementation(async (_id, mode, minutes) => ({
    ...initial, mode, interval_minutes: minutes,
  }))
})

describe('ESP32 data capture settings', () => {
  it('starts in Live and saves selected timed interval through the API', async () => {
    render(<Esp32CaptureSettings systemId="system-1" canManage />)
    expect(await screen.findByText('ESP32 data collection')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByLabelText(/Live — save/)).toBeChecked())
    fireEvent.click(screen.getByLabelText(/Timed — save/))
    fireEvent.change(screen.getByLabelText('Saving interval'), { target: { value: '30' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save ESP32 collection settings' }))
    await waitFor(() => {
      expect(updateEsp32CaptureSettings).toHaveBeenCalledWith('system-1', 'timed', 30)
    })
    expect(await screen.findByText('ESP32 collection settings saved.')).toBeInTheDocument()
  })

  it('blocks invalid custom intervals before submitting', async () => {
    render(<Esp32CaptureSettings systemId="system-1" canManage />)
    await waitFor(() => expect(screen.getByLabelText(/Live — save/)).toBeChecked())
    fireEvent.click(screen.getByLabelText(/Timed — save/))
    fireEvent.change(screen.getByLabelText('Saving interval'), { target: { value: 'custom' } })
    fireEvent.change(screen.getByLabelText(/Custom interval/), { target: { value: '0' } })
    expect(screen.getByRole('button', { name: 'Save ESP32 collection settings' })).toBeDisabled()
    expect(updateEsp32CaptureSettings).not.toHaveBeenCalled()
  })

  it('restricts editing for non-administrators', async () => {
    render(<Esp32CaptureSettings systemId="system-1" canManage={false} />)
    await waitFor(() => expect(screen.getByLabelText(/Live — save/)).toBeChecked())
    expect(screen.getByLabelText(/Timed — save/)).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Save ESP32 collection settings' })).not.toBeInTheDocument()
  })
})
