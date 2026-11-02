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
  CALIBRATION_HISTORY_PAGE_SIZE,
  createFeederCalibration,
  deleteFeederCalibration,
  loadFeederCalibrationHistoryPage,
  updateFeederCalibration,
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


function makeCalibration(
  index: number,
) {
  return {
    id:
      `calibration-${index}`,

    actuator_id:
      'actuator-1',

    run_count:
      index + 1,

    measured_seconds:
      10,

    measured_grams:
      50,

    grams_per_second:
      5,

    calibration_method:
      'measured_average',

    performed_at:
      '2026-09-12T10:00:00Z',

    verified_by_user_id:
      null,

    notes:
      null,
  }
}


describe(
  'feeding calibration service',
  () => {
    beforeEach(() => {
      mockedApiRequest
        .mockReset()
    })


    it(
      'uses a 51-row lookahead for bounded calibration history',
      async () => {
        const calibrations =
          Array.from(
            {
              length:
                CALIBRATION_HISTORY_PAGE_SIZE +
                1,
            },
            (_, index) =>
              makeCalibration(
                index,
              ),
          )

        mockedApiRequest
          .mockResolvedValueOnce(
            calibrations,
          )

        const result =
          await loadFeederCalibrationHistoryPage(
            'actuator / one',
            50,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/calibrations/history?' +
          'actuator_id=actuator%20%2F%20one' +
          '&limit=51' +
          '&offset=50',
        )

        expect(
          result.calibrations,
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
          true,
        )

        expect(
          result.offset,
        ).toBe(
          50,
        )

        expect(
          result.calibrations[0]?.id,
        ).toBe(
          'calibration-0',
        )

        expect(
          result.calibrations[49]?.id,
        ).toBe(
          'calibration-49',
        )
      },
    )


    it(
      'normalizes a negative calibration history offset',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            [],
          )

        const result =
          await loadFeederCalibrationHistoryPage(
            'actuator-1',
            -50,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/calibrations/history?' +
          'actuator_id=actuator-1' +
          '&limit=51' +
          '&offset=0',
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
      'creates calibration using the exact backend fields',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            makeCalibration(
              0,
            ),
          )

        await createFeederCalibration(
          'actuator-1',
          {
            run_count:
              5,

            measured_seconds:
              10,

            measured_grams:
              50,

            grams_per_second:
              5,

            calibration_method:
              'measured_average',

            performed_at:
              '2026-09-12T10:00:00Z',

            verified_by_user_id:
              null,

            notes:
              'Bench measurement.',
          },
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/calibrations',
          {
            method:
              'POST',

            body:
              JSON.stringify({
                actuator_id:
                  'actuator-1',

                run_count:
                  5,

                measured_seconds:
                  10,

                measured_grams:
                  50,

                grams_per_second:
                  5,

                calibration_method:
                  'measured_average',

                performed_at:
                  '2026-09-12T10:00:00Z',

                verified_by_user_id:
                  null,

                notes:
                  'Bench measurement.',
              }),
          },
        )
      },
    )


    it(
      'updates calibration using only supplied fields',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            makeCalibration(
              0,
            ),
          )

        await updateFeederCalibration(
          'calibration / one',
          {
            grams_per_second:
              5.25,

            verified_by_user_id:
              'admin-user-id',
          },
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/calibrations/calibration%20%2F%20one',
          {
            method:
              'PATCH',

            body:
              JSON.stringify({
                grams_per_second:
                  5.25,

                verified_by_user_id:
                  'admin-user-id',
              }),
          },
        )
      },
    )


    it(
      'deletes calibration using the encoded calibration id',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            undefined,
          )

        await deleteFeederCalibration(
          'calibration / one',
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'feeding/calibrations/calibration%20%2F%20one',
          {
            method:
              'DELETE',
          },
        )
      },
    )
  },
)