import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { getActuator, loadActuatorHistoryPage } from '../services/actuatorService'
import type { ActuatorEvent, ActuatorHistoryPage } from '../services/actuatorService'
import type { DashboardActuator } from '../types/dashboard'
import { ActuatorDetailPage } from './ActuatorDetailPage'

vi.mock('../services/actuatorService', () => ({
  getActuator: vi.fn(), loadActuatorHistoryPage: vi.fn(), ACTUATOR_HISTORY_PAGE_SIZE: 50,
}))

const actuator: DashboardActuator = {
  id: 'a', system_id: 's', name: 'Test pump', actuator_type: 'water_pump',
  control_mode: 'manual', hardware_identifier: null, location_type: null, location_id: null,
  is_enabled: true, safety_config: null, current_state: 'off', current_value: 0,
  last_state_at: null, created_at: '2026-09-07T00:00:00Z', updated_at: '2026-09-07T00:00:00Z', deleted_at: null,
}
const event: ActuatorEvent = {
  id: 'e', actuator_id: 'a', command_type: 'set_value', requested_value: 0, actual_value: 0,
  started_at: '2026-09-07T00:00:00Z', completed_at: null, duration_ms: 0,
  trigger_source: 'manual', status: 'pending', fault_code: null, error_message: null,
  created_at: '2026-09-07T00:00:01Z',
}
const page: ActuatorHistoryPage = { events: [event], offset: 0, hasNext: false, hasPrevious: false }

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/actuators/a']}>
      <Link to="/actuators/b">Another actuator</Link>
      <Routes>
        <Route path="/actuators/:actuatorId" element={<ActuatorDetailPage />} />
        <Route path="/actuators" element={<h1>Actuator overview</h1>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getActuator).mockResolvedValue(actuator)
  vi.mocked(loadActuatorHistoryPage).mockResolvedValue(page)
})

it('renders persisted records, nulls and zeros without actuator controls and links back', async () => {
  renderPage()
  await screen.findByRole('table', { name: 'Persisted software event history' })
  expect(getActuator).toHaveBeenCalledWith('a')
  expect(loadActuatorHistoryPage).toHaveBeenCalledWith('a', 0)
  expect(screen.getByText('No state recorded')).toBeInTheDocument()
  const table = screen.getByRole('table')
  expect(within(table).getAllByText('0')).toHaveLength(3)
  expect(within(table).getAllByText('Not recorded')).toHaveLength(3)
  expect(within(table).getByText('set value')).toBeInTheDocument()
  expect(screen.getByText(/do not confirm physical actuator execution/)).toBeInTheDocument()
  expect(screen.getAllByRole('button').map(button => button.textContent)).toEqual(['Previous', 'Next'])
  expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  fireEvent.click(screen.getByRole('link', { name: '← Actuators' }))
  expect(screen.getByRole('heading', { name: 'Actuator overview' })).toBeInTheDocument()
})

it('shows timestamped persisted state and zero value', async () => {
  vi.mocked(getActuator).mockResolvedValue({ ...actuator, last_state_at: event.started_at })
  renderPage()
  await screen.findByRole('heading', { name: 'Test pump' })
  expect(screen.queryByText('No state recorded')).not.toBeInTheDocument()
  expect(screen.getByText('off')).toBeInTheDocument()
  expect(screen.getByText('Value').nextElementSibling).toHaveTextContent('0')
})

it('shows detail and history loading states followed by empty history', async () => {
  const detailRequest = deferred<DashboardActuator>()
  const historyRequest = deferred<ActuatorHistoryPage>()
  vi.mocked(getActuator).mockReturnValue(detailRequest.promise)
  vi.mocked(loadActuatorHistoryPage).mockReturnValue(historyRequest.promise)
  renderPage()
  expect(screen.getByText('Loading actuator...')).toBeInTheDocument()
  await act(async () => detailRequest.resolve(actuator))
  expect(screen.getByText('Loading event history...')).toBeInTheDocument()
  await act(async () => historyRequest.resolve({ ...page, events: [] }))
  expect(screen.getByText('No persisted software events on this page.')).toBeInTheDocument()
})

it.each(['detail', 'history'])('shows a %s request error', async target => {
  if (target === 'detail') vi.mocked(getActuator).mockRejectedValue(new Error('Not found'))
  else vi.mocked(loadActuatorHistoryPage).mockRejectedValue(new Error('Unavailable'))
  renderPage()
  expect(await screen.findByRole('alert')).toHaveTextContent(target === 'detail'
    ? 'Unable to load this actuator.' : 'Unable to load actuator event history.')
})

it('paginates by 50 without reloading detail, hides previous rows during loading and can return', async () => {
  const second = deferred<ActuatorHistoryPage>()
  vi.mocked(loadActuatorHistoryPage)
    .mockResolvedValueOnce({ ...page, hasNext: true })
    .mockReturnValueOnce(second.promise)
    .mockResolvedValueOnce(page)
  renderPage()
  await screen.findByRole('table')
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  await waitFor(() => expect(loadActuatorHistoryPage).toHaveBeenLastCalledWith('a', 50))
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
  await act(async () => second.resolve({ ...page, events: [], offset: 50, hasPrevious: true }))
  expect(screen.getByText('Page 2')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Previous' }))
  await screen.findByRole('table')
  expect(loadActuatorHistoryPage).toHaveBeenLastCalledWith('a', 0)
  expect(getActuator).toHaveBeenCalledTimes(1)
})

it('resets pagination on route change and ignores an obsolete history response', async () => {
  const obsolete = deferred<ActuatorHistoryPage>()
  vi.mocked(getActuator).mockImplementation(async id => ({ ...actuator, id, name: `Pump ${id}` }))
  vi.mocked(loadActuatorHistoryPage)
    .mockResolvedValueOnce({ ...page, hasNext: true })
    .mockReturnValueOnce(obsolete.promise)
    .mockResolvedValueOnce({ ...page, events: [] })
  renderPage()
  await screen.findByRole('table')
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  await waitFor(() => expect(loadActuatorHistoryPage).toHaveBeenLastCalledWith('a', 50))
  fireEvent.click(screen.getByRole('link', { name: 'Another actuator' }))
  await screen.findByRole('heading', { name: 'Pump b' })
  expect(loadActuatorHistoryPage).toHaveBeenLastCalledWith('b', 0)
  await act(async () => obsolete.resolve({ ...page, offset: 50 }))
  expect(screen.getByText('Page 1')).toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Pump a' })).not.toBeInTheDocument()
})

it('ignores an obsolete actuator detail response', async () => {
  const obsolete = deferred<DashboardActuator>()
  vi.mocked(getActuator).mockReturnValueOnce(obsolete.promise)
    .mockResolvedValueOnce({ ...actuator, id: 'b', name: 'Second pump' })
  renderPage()
  fireEvent.click(screen.getByRole('link', { name: 'Another actuator' }))
  await screen.findByRole('heading', { name: 'Second pump' })
  await act(async () => obsolete.resolve(actuator))
  expect(screen.getByRole('heading', { name: 'Second pump' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Test pump' })).not.toBeInTheDocument()
})
