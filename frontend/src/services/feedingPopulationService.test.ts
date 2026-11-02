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
  createFishPopulationRecord,
  deleteFishPopulationRecord,
  loadFishPopulationHistoryPage,
  updateFishPopulationRecord,
} from './feedingService'


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


describe(
  'fish population feeding service',
  () => {
    beforeEach(() => {
      mockedApiRequest
        .mockReset()
    })


    it(
      'uses a 51-row lookahead and exposes only 50 records',
      async () => {
        const records =
          Array.from(
            {
              length: 51,
            },
            (_, index) => ({
              id:
                `population-${index}`,

              tank_id:
                'tank-1',

              species:
                'Tilapia',

              count:
                100 + index,

              estimated_biomass_grams:
                25000 + index,

              effective_at:
                `2026-09-01T00:${String(
                  index,
                ).padStart(
                  2,
                  '0',
                )}:00Z`,

              recorded_by_user_id:
                null,

              notes:
                null,
            }),
          )

        mockedApiRequest
          .mockResolvedValueOnce(
            records,
          )

        const result =
          await loadFishPopulationHistoryPage(
            'tank-1',
            0,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/population/history?tank_id=tank-1&limit=51&offset=0',
        )

        expect(
          result.records,
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
      'normalizes a negative history offset to zero',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            [],
          )

        const result =
          await loadFishPopulationHistoryPage(
            'tank 1',
            -50,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/population/history?tank_id=tank%201&limit=51&offset=0',
        )

        expect(
          result.offset,
        ).toBe(
          0,
        )
      },
    )


    it(
      'creates a population record with the selected tank and backend fields',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce({
            id:
              'population-1',

            tank_id:
              'tank-1',

            species:
              'Tilapia',

            count:
              100,

            estimated_biomass_grams:
              25000,

            effective_at:
              '2026-09-14T01:00:00Z',

            recorded_by_user_id:
              'user-1',

            notes:
              'Sampling record.',
          })

        await createFishPopulationRecord(
          'tank-1',
          {
            species:
              'Tilapia',

            count:
              100,

            estimated_biomass_grams:
              25000,

            effective_at:
              '2026-09-14T01:00:00Z',

            notes:
              'Sampling record.',
          },
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/population',
          {
            method:
              'POST',

            body:
              JSON.stringify({
                tank_id:
                  'tank-1',

                species:
                  'Tilapia',

                count:
                  100,

                estimated_biomass_grams:
                  25000,

                effective_at:
                  '2026-09-14T01:00:00Z',

                notes:
                  'Sampling record.',
              }),
          },
        )
      },
    )


    it(
      'updates only supplied population fields',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce({
            id:
              'population-1',

            tank_id:
              'tank-1',

            species:
              'Tilapia',

            count:
              95,

            estimated_biomass_grams:
              24000,

            effective_at:
              '2026-09-14T01:00:00Z',

            recorded_by_user_id:
              'user-1',

            notes:
              null,
          })

        await updateFishPopulationRecord(
          'population/1',
          {
            count:
              95,

            estimated_biomass_grams:
              24000,
          },
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/population/population%2F1',
          {
            method:
              'PATCH',

            body:
              JSON.stringify({
                count:
                  95,

                estimated_biomass_grams:
                  24000,
              }),
          },
        )
      },
    )


    it(
      'encodes the population record id when deleting',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            undefined,
          )

        await deleteFishPopulationRecord(
          'population/1',
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/population/population%2F1',
          {
            method:
              'DELETE',
          },
        )
      },
    )
  },
)