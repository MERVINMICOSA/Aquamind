import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import type {
  RefillEvent,
} from '../types/refill'

import {
  apiRequest,
} from './apiClient'

import {
  loadRefillHistoryPage,
  listSystemReservoirs,
} from './refillService'


vi.mock(
  './apiClient',
  () => ({
    apiRequest:
      vi.fn(),
  }),
)


const mockedApiRequest =
  vi.mocked(
    apiRequest,
  )


function buildEvent(
  index: number,
): RefillEvent {
  return {
    id:
      `event-${index}`,

    reservoir_id:
      'reservoir-1',

    target_tank_id:
      'tank-1',

    start_level_percent:
      20,

    end_level_percent:
      40,

    started_at:
      '2026-09-20T00:00:00Z',

    completed_at:
      '2026-09-20T00:05:00Z',

    duration_seconds:
      300,

    trigger:
      'automatic',

    status:
      'completed',

    timeout_reason:
      null,

    created_at:
      '2026-09-20T00:05:00Z',
  }
}


beforeEach(
  () => {
    mockedApiRequest
      .mockReset()
  },
)


describe(
  'refillService',
  () => {
    it(
      'lists reservoirs for one encoded system',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            [],
          )

        await listSystemReservoirs(
          'system / one',
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          (
            'reservoirs?system_id='
            + 'system%20%2F%20one'
          ),
        )
      },
    )


    it(
      'loads a bounded refill history page with lookahead',
      async () => {
        const rows =
          Array.from(
            {
              length:
                51,
            },
            (
              _,
              index,
            ) =>
              buildEvent(
                index,
              ),
          )

        mockedApiRequest
          .mockResolvedValueOnce(
            rows,
          )

        const result =
          await loadRefillHistoryPage(
            'reservoir / one',
            0,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          (
            'refill-events/history'
            + '?reservoir_id=reservoir%20%2F%20one'
            + '&limit=51'
            + '&offset=0'
          ),
        )

        expect(
          result.events,
        ).toHaveLength(
          50,
        )

        expect(
          result.hasNext,
        ).toBe(
          true,
        )

        expect(
          result.hasPrevious,
        ).toBe(
          false,
        )

        expect(
          result.offset,
        ).toBe(
          0,
        )
      },
    )


    it(
      'reports the final bounded page without next',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            [
              buildEvent(
                1,
              ),
            ],
          )

        const result =
          await loadRefillHistoryPage(
            'reservoir-1',
            50,
          )

        expect(
          result.events,
        ).toHaveLength(
          1,
        )

        expect(
          result.hasNext,
        ).toBe(
          false,
        )

        expect(
          result.hasPrevious,
        ).toBe(
          true,
        )

        expect(
          result.offset,
        ).toBe(
          50,
        )
      },
    )


    it(
      'normalizes invalid negative and fractional offsets',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            [],
          )

        const result =
          await loadRefillHistoryPage(
            'reservoir-1',
            -10.9,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          (
            'refill-events/history'
            + '?reservoir_id=reservoir-1'
            + '&limit=51'
            + '&offset=0'
          ),
        )

        expect(
          result.offset,
        ).toBe(
          0,
        )
      },
    )
  },
)