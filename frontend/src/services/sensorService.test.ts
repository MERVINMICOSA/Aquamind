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
  getSensor,
  loadSensorHistoryPage,
  loadSystemSensorOverview,
  SENSOR_HISTORY_PAGE_SIZE,
} from './sensorService'


vi.mock(
  './apiClient',
  () => ({
    apiRequest:
      vi.fn(),
  }),
)


describe(
  'sensor service',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })


    it(
      'loads only sensors and latest readings for the selected system',
      async () => {
        vi.mocked(
          apiRequest,
        )
          .mockResolvedValueOnce(
            [],
          )
          .mockResolvedValueOnce(
            [],
          )


        await loadSystemSensorOverview(
          'system-1',
        )


        expect(
          apiRequest,
        ).toHaveBeenCalledTimes(
          2,
        )


        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'sensors?system_id=system-1',
        )


        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'sensor-readings/latest?system_id=system-1',
        )
      },
    )


    it(
      'returns the sensor overview resources',
      async () => {
        const sensors = [
          {
            id:
              'sensor-1',
          },
        ]

        const latestReadings = [
          {
            id:
              'reading-1',
          },
        ]


        vi.mocked(
          apiRequest,
        )
          .mockResolvedValueOnce(
            sensors,
          )
          .mockResolvedValueOnce(
            latestReadings,
          )


        const result =
          await loadSystemSensorOverview(
            'system-1',
          )


        expect(
          result,
        ).toEqual({
          sensors,
          latestReadings,
        })
      },
    )


    it(
      'loads one sensor directly by id',
      async () => {
        const sensor = {
          id:
            'sensor-1',
        }


        vi.mocked(
          apiRequest,
        ).mockResolvedValueOnce(
          sensor,
        )


        const result =
          await getSensor(
            'sensor-1',
          )


        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'sensors/sensor-1',
        )


        expect(
          result,
        ).toBe(
          sensor,
        )
      },
    )


    it(
      'uses one lookahead history row to determine whether another page exists',
      async () => {
        const readings =
          Array.from(
            {
              length:
                SENSOR_HISTORY_PAGE_SIZE +
                1,
            },
            (
              _,
              index,
            ) => ({
              id:
                `reading-${index}`,
            }),
          )


        vi.mocked(
          apiRequest,
        ).mockResolvedValueOnce(
          readings,
        )


        const result =
          await loadSensorHistoryPage(
            'sensor-1',
            0,
          )


        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'sensor-readings/history?sensor_id=sensor-1&limit=51&offset=0',
        )


        expect(
          result.readings,
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
      },
    )
  },
)