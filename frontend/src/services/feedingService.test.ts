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
  FEEDING_HISTORY_PAGE_SIZE,
  listFeedingSchedules,
  loadFeedingEventHistoryPage,
} from './feedingService'

import type {
  FeedingEvent,
} from '../types/feeding'

import {
  createFeedingSchedule,
  deleteFeedingSchedule,
  updateFeedingSchedule,
} from './feedingService'

vi.mock(
  './apiClient',
  () => ({
    apiRequest: vi.fn(),
  }),
)


const mockedApiRequest =
  vi.mocked(
    apiRequest,
  )


function makeEvent(
  index: number,
): FeedingEvent {
  return {
    id: `event-${index}`,
    schedule_id: null,
    actuator_event_id:
      `actuator-event-${index}`,
    tank_id: 'tank-1',
    amount_grams: index,
    duration_seconds: index,
    calculated_from_biomass: null,
    calibration_id: null,
    executed_at:
      '2026-09-08T00:00:00Z',
    status: 'completed',
    notes: null,
  }
}


describe(
  'feedingService',
  () => {
    beforeEach(() => {
      mockedApiRequest
        .mockReset()
    })


    it(
      'loads schedules for the encoded system',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            [],
          )

        await listFeedingSchedules(
          'system / one',
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/schedules?' +
          'system_id=system%20%2F%20one',
        )
      },
    )


    it(
      'uses a 51-row lookahead for feeding history',
      async () => {
        const events =
          Array.from(
            {
              length:
                FEEDING_HISTORY_PAGE_SIZE +
                1,
            },
            (_, index) =>
              makeEvent(index),
          )

        mockedApiRequest
          .mockResolvedValueOnce(
            events,
          )

        const result =
          await loadFeedingEventHistoryPage(
            'system-1',
            50,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/events/history?' +
          'system_id=system-1' +
          '&limit=51' +
          '&offset=50',
        )

        expect(
          result.events,
        ).toHaveLength(
          50,
        )

        expect(
          result.hasNext,
        ).toBe(true)

        expect(
          result.hasPrevious,
        ).toBe(true)

        expect(
          result.offset,
        ).toBe(50)

        expect(
          result.events[0]?.id,
        ).toBe(
          'event-0',
        )

        expect(
          result.events[49]?.id,
        ).toBe(
          'event-49',
        )
      },
    )


    it(
      'normalizes a negative history offset to zero',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            [],
          )

        const result =
          await loadFeedingEventHistoryPage(
            'system-1',
            -40,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/events/history?' +
          'system_id=system-1' +
          '&limit=51' +
          '&offset=0',
        )

        expect(
          result.hasPrevious,
        ).toBe(false)

        expect(
          result.offset,
        ).toBe(0)
      },
    )


    it(
  'creates a feeding schedule for the selected system',
  async () => {
    mockedApiRequest
      .mockResolvedValueOnce(
        {},
      )

    await createFeedingSchedule(
      'system-1',
      {
        actuator_id:
          'actuator-1',

        name:
          'Morning Feeding',

        schedule_expression:
          '0 8 * * *',

        enabled: true,

        max_per_feed_grams:
          100,
      },
    )

    expect(
      mockedApiRequest,
    ).toHaveBeenCalledWith(
      'feeding/schedules',
      {
        method: 'POST',

        body: JSON.stringify({
          system_id:
            'system-1',

          actuator_id:
            'actuator-1',

          name:
            'Morning Feeding',

          schedule_expression:
            '0 8 * * *',

          enabled: true,

          max_per_feed_grams:
            100,
        }),
      },
    )
  },
)


it(
  'updates a feeding schedule using the encoded schedule id',
  async () => {
    mockedApiRequest
      .mockResolvedValueOnce(
        {},
      )

    await updateFeedingSchedule(
      'schedule / one',
      {
        enabled: false,
        max_per_feed_grams:
          120,
      },
    )

    expect(
      mockedApiRequest,
    ).toHaveBeenCalledWith(
      'feeding/schedules/schedule%20%2F%20one',
      {
        method: 'PATCH',

        body: JSON.stringify({
          enabled: false,
          max_per_feed_grams:
            120,
        }),
      },
    )
  },
)


    it(
    'deletes a feeding schedule using the encoded schedule id',
    async () => {
        mockedApiRequest
        .mockResolvedValueOnce(
            undefined,
        )

        await deleteFeedingSchedule(
        'schedule / one',
        )

        expect(
        mockedApiRequest,
        ).toHaveBeenCalledWith(
        'feeding/schedules/schedule%20%2F%20one',
        {
            method: 'DELETE',
        },
        )
    },
    )

  },
)