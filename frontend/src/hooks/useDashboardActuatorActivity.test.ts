import {
  renderHook,
  waitFor,
} from '@testing-library/react'
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  loadActuatorHistoryPage,
} from '../services/actuatorService'

import {
  useDashboardActuatorActivity,
} from './useDashboardActuatorActivity'


vi.mock(
  '../services/actuatorService',
  () => ({
    loadActuatorHistoryPage:
      vi.fn(),
  }),
)


const EVENT = {
  id: 'event-1',
  actuator_id: 'actuator-1',
  command_type: 'set_state',
  requested_value: 1,
  actual_value: 1,
  started_at: '2026-09-06T06:00:00Z',
  completed_at: '2026-09-06T06:00:01Z',
  duration_ms: 1000,
  trigger_source: 'automation',
  status: 'completed',
  fault_code: null,
  error_message: null,
  created_at: '2026-09-06T06:00:00Z',
}


describe(
  'useDashboardActuatorActivity',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })


    it(
      'stays idle without a selected actuator',
      () => {
        const { result } = renderHook(
          () => useDashboardActuatorActivity(null),
        )

        expect(result.current).toEqual({
          events: [],
          status: 'idle',
          errorMessage: null,
        })

        expect(
          loadActuatorHistoryPage,
        ).not.toHaveBeenCalled()
      },
    )


    it(
      'loads page zero of the canonical actuator history',
      async () => {
        vi.mocked(
          loadActuatorHistoryPage,
        ).mockResolvedValue({
          events: [EVENT],
          offset: 0,
          hasNext: false,
          hasPrevious: false,
        })

        const { result } = renderHook(
          () => useDashboardActuatorActivity('actuator-1'),
        )

        expect(result.current.status).toBe('loading')

        await waitFor(() => {
          expect(result.current.status).toBe('ready')
        })

        expect(
          loadActuatorHistoryPage,
        ).toHaveBeenCalledWith(
          'actuator-1',
          0,
        )

        expect(result.current.events).toEqual([EVENT])
      },
    )


    it(
      'exposes an honest error state when history loading fails',
      async () => {
        vi.mocked(
          loadActuatorHistoryPage,
        ).mockRejectedValue(
          new Error('Unavailable'),
        )

        const { result } = renderHook(
          () => useDashboardActuatorActivity('actuator-1'),
        )

        await waitFor(() => {
          expect(result.current.status).toBe('error')
        })

        expect(result.current.events).toEqual([])
        expect(result.current.errorMessage).toBe(
          'Unable to load persisted actuator activity.',
        )
      },
    )
  },
)
