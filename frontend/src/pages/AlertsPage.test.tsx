import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { listSystems } from '../services/dashboardService'
import { loadAlertHistoryPage } from '../services/alertService'
import type { AlertHistoryPage } from '../services/alertService'
import type { AquaponicsSystem, DashboardAlert } from '../types/dashboard'
import { AlertsPage } from './AlertsPage'

vi.mock('../services/dashboardService', () => ({ listSystems: vi.fn() }))
vi.mock('../services/alertService', () => ({ loadAlertHistoryPage: vi.fn(), ALERT_HISTORY_PAGE_SIZE: 50 }))

const systems: AquaponicsSystem[] = ['Alpha', 'Beta'].map((name, index) => ({
  id: `s${index}`, name, description: null, timezone: 'UTC', is_active: true,
  created_at: '2026-09-07T00:00:00Z', updated_at: '2026-09-07T00:00:00Z',
}))
const alert: DashboardAlert = {
  id: 'a', system_id: 's0', sensor_id: null, actuator_id: null, threshold_id: null,
  alert_type: 'test', severity: 'warning', status: 'active', message: 'Persisted test alert',
  trigger_value: 0, created_at: '2026-09-07T00:00:00Z', acknowledged_at: null,
  acknowledged_by_user_id: null, resolved_at: null, resolution_reason: null,
}
const page: AlertHistoryPage = { alerts: [alert], hasNext: false, hasPrevious: false, offset: 0 }

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: Error) => void
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listSystems).mockResolvedValue([...systems].reverse())
  vi.mocked(loadAlertHistoryPage).mockResolvedValue(page)
})

it('selects the first alphabetical system and renders persisted metadata, nulls and zero', async () => {
  render(<AlertsPage />)
  const table = await screen.findByRole('table', { name: 'Persisted alert history' })
  expect(screen.getByRole('combobox')).toHaveValue('s0')
  expect(loadAlertHistoryPage).toHaveBeenCalledExactlyOnceWith('s0', 0)
  expect(within(table).getByText('warning')).toBeInTheDocument()
  expect(within(table).getByText('active')).toBeInTheDocument()
  expect(within(table).getByText('test')).toBeInTheDocument()
  expect(within(table).getByText('Persisted test alert')).toBeInTheDocument()
  expect(within(table).getByText('0')).toBeInTheDocument()
  expect(within(table).getAllByText('Not recorded')).toHaveLength(7)
  expect(within(table).getByText(new Date(alert.created_at).toLocaleString())).toBeInTheDocument()
  expect(screen.getByText('Alert history is persisted application data, not hardware evidence.')).toBeInTheDocument()
  expect(screen.getAllByRole('button').map(button => button.textContent)).toEqual(['Previous', 'Next'])
  expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
})

it('renders populated resource and lifecycle metadata and a null trigger value', async () => {
  const populated = { ...alert, sensor_id: 'sensor-1', actuator_id: 'actuator-1', threshold_id: 'threshold-1',
    trigger_value: null, acknowledged_at: '2026-09-07T01:00:00Z', acknowledged_by_user_id: 'user-1',
    resolved_at: '2026-09-07T02:00:00Z', resolution_reason: 'Recorded resolution', status: 'resolved' }
  vi.mocked(loadAlertHistoryPage).mockResolvedValue({ ...page, alerts: [populated] })
  render(<AlertsPage />)
  const table = await screen.findByRole('table')
  for (const value of ['sensor-1', 'actuator-1', 'threshold-1', 'user-1', 'Recorded resolution', 'resolved',
    new Date(populated.acknowledged_at).toLocaleString(), new Date(populated.resolved_at).toLocaleString()]) {
    expect(within(table).getByText(value)).toBeInTheDocument()
  }
  expect(within(table).getAllByText('Not recorded')).toHaveLength(1)
})

it('shows system loading then no-system without requesting history', async () => {
  const pending = deferred<AquaponicsSystem[]>()
  vi.mocked(listSystems).mockReturnValue(pending.promise)
  render(<AlertsPage />)
  expect(screen.getByText('Loading AquaMind systems...')).toBeInTheDocument()
  expect(loadAlertHistoryPage).not.toHaveBeenCalled()
  await act(async () => pending.resolve([]))
  expect(screen.getByRole('heading', { name: 'No aquaponics system configured' })).toBeInTheDocument()
  expect(loadAlertHistoryPage).not.toHaveBeenCalled()
})

it('shows history loading followed by an empty page', async () => {
  const pending = deferred<AlertHistoryPage>()
  vi.mocked(loadAlertHistoryPage).mockReturnValue(pending.promise)
  render(<AlertsPage />)
  await screen.findByText('Loading alert history...')
  await act(async () => pending.resolve({ ...page, alerts: [] }))
  expect(screen.getByText('No persisted alerts on this page.')).toBeInTheDocument()
})

it.each(['systems', 'history'])('reports %s errors honestly', async target => {
  if (target === 'systems') vi.mocked(listSystems).mockRejectedValue(new Error('Unavailable'))
  else vi.mocked(loadAlertHistoryPage).mockRejectedValue(new Error('Unavailable'))
  render(<AlertsPage />)
  expect(await screen.findByRole('alert')).toHaveTextContent(target === 'systems'
    ? 'Unable to load AquaMind systems.' : 'Unable to load alert history for the selected system.')
  expect(screen.queryByText('No persisted alerts on this page.')).not.toBeInTheDocument()
})

it('paginates by 50 without reloading systems and permits returning after a page error', async () => {
  const pending = deferred<AlertHistoryPage>()
  vi.mocked(loadAlertHistoryPage).mockResolvedValueOnce({ ...page, hasNext: true })
    .mockReturnValueOnce(pending.promise).mockResolvedValueOnce(page)
  render(<AlertsPage />)
  await screen.findByRole('table')
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  await waitFor(() => expect(loadAlertHistoryPage).toHaveBeenLastCalledWith('s0', 50))
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  await act(async () => pending.reject(new Error('Unavailable')))
  expect(screen.getByText('Page 2')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Previous' }))
  await screen.findByRole('table')
  expect(loadAlertHistoryPage).toHaveBeenLastCalledWith('s0', 0)
  expect(screen.getByText('Page 1')).toBeInTheDocument()
  expect(listSystems).toHaveBeenCalledTimes(1)
})

it('resets system pagination and ignores responses from an obsolete page', async () => {
  const obsolete = deferred<AlertHistoryPage>()
  vi.mocked(loadAlertHistoryPage).mockResolvedValueOnce({ ...page, hasNext: true })
    .mockReturnValueOnce(obsolete.promise).mockResolvedValueOnce({ ...page, alerts: [] })
  render(<AlertsPage />)
  await screen.findByRole('table')
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  await waitFor(() => expect(loadAlertHistoryPage).toHaveBeenLastCalledWith('s0', 50))
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 's1' } })
  await screen.findByText('No persisted alerts on this page.')
  expect(loadAlertHistoryPage).toHaveBeenLastCalledWith('s1', 0)
  await act(async () => obsolete.resolve({ ...page, offset: 50 }))
  expect(screen.getByText('Page 1')).toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})

it('hides old data when returning to a previously loaded system', async () => {
  const pending = deferred<AlertHistoryPage>()
  vi.mocked(loadAlertHistoryPage).mockResolvedValueOnce(page)
    .mockResolvedValueOnce({ ...page, alerts: [] }).mockReturnValueOnce(pending.promise)
  render(<AlertsPage />)
  await screen.findByRole('table')
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 's1' } })
  await screen.findByText('No persisted alerts on this page.')
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 's0' } })
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  expect(screen.getByText('Loading alert history...')).toBeInTheDocument()
  await act(async () => pending.resolve(page))
  expect(screen.getByRole('table')).toBeInTheDocument()
})
