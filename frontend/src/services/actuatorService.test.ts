import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  apiRequest,
} from './apiClient'

import {
  getActuator,
  loadActuatorHistoryPage,
  loadSystemActuatorOverview,
} from './actuatorService'


vi.mock(
  './apiClient',
  () => ({
    apiRequest:
      vi.fn(),
  }),
)


describe(
  'actuator service',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })


    it(
      'loads actuators only for the selected system',
      async () => {
        vi.mocked(
          apiRequest,
        ).mockResolvedValueOnce(
          [],
        )


        await loadSystemActuatorOverview(
          'system-1',
        )


        expect(
          apiRequest,
        ).toHaveBeenCalledTimes(
          1,
        )


        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'actuators?system_id=system-1',
        )
      },
    )


    it(
      'returns the actuator resources',
      async () => {
        const actuators = [
          {
            id:
              'actuator-1',
          },
        ]


        vi.mocked(
          apiRequest,
        ).mockResolvedValueOnce(
          actuators,
        )


        const result =
          await loadSystemActuatorOverview(
            'system-1',
          )


        expect(
          result,
        ).toEqual({
          actuators,
        })
      },
    )
  },
)

it('loads an encoded actuator detail ID', async () => {
  const actuator = { id: 'actuator/1' }
  vi.mocked(apiRequest).mockResolvedValueOnce(actuator)
  expect(await getActuator('actuator/1')).toEqual(actuator)
  expect(apiRequest).toHaveBeenLastCalledWith('actuators/actuator%2F1')
})

it.each([0, 50, 51])('uses lookahead with %i rows and preserves server order', async count => {
  const events = Array.from({ length: count }, (_, index) => ({ id: `event-${count - index}` }))
  vi.mocked(apiRequest).mockResolvedValueOnce(events)
  const page = await loadActuatorHistoryPage('actuator/1', 50)
  expect(apiRequest).toHaveBeenLastCalledWith('actuator-events/history?actuator_id=actuator%2F1&limit=51&offset=50')
  expect(page).toEqual({ events: events.slice(0, 50), hasNext: count > 50, hasPrevious: true, offset: 50 })
})

it.each([[-3, 0], [0, 0], [50.9, 50]])('normalizes offset %s to %s', async (offset, expected) => {
  vi.mocked(apiRequest).mockResolvedValueOnce([])
  const page = await loadActuatorHistoryPage('a', offset)
  expect(apiRequest).toHaveBeenLastCalledWith(`actuator-events/history?actuator_id=a&limit=51&offset=${expected}`)
  expect(page.offset).toBe(expected)
  expect(page.hasPrevious).toBe(expected > 0)
})
