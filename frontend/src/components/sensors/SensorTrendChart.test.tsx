import {
  render,
  screen,
} from '@testing-library/react'

import {
  describe,
  expect,
  it,
} from 'vitest'

import {
  SensorTrendChart,
} from './SensorTrendChart'

import type {
  DashboardSensorReading,
} from '../../types/dashboard'


function createReading(
  id: string,
  recordedAt: string,
  value: number,
): DashboardSensorReading {
  return {
    id,

    sensor_id:
      'sensor-1',

    recorded_at:
      recordedAt,

    value_numeric:
      value,

    unit:
      'pH',

    quality_status:
      'good',

    source:
      'simulator',

    sequence_number:
      null,

    created_at:
      recordedAt,
  }
}


describe(
  'SensorTrendChart',
  () => {
    it(
      'shows an honest empty state when fewer than two readings are available',
      () => {
        render(
          <SensorTrendChart
            readings={[
              createReading(
                'reading-1',
                '2026-09-06T08:00:00Z',
                7,
              ),
            ]}
            unit="pH"
          />,
        )


        expect(
          screen.getByText(
            'Not enough readings for a trend',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'renders an accessible chart when at least two valid readings exist',
      () => {
        render(
          <SensorTrendChart
            readings={[
              createReading(
                'reading-2',
                '2026-09-06T08:01:00Z',
                7.2,
              ),

              createReading(
                'reading-1',
                '2026-09-06T08:00:00Z',
                7,
              ),
            ]}
            unit="pH"
          />,
        )


        expect(
          screen.getByRole(
            'img',
            {
              name:
                'Sensor reading trend',
            },
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByText(
            '2 readings on this page',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'shows the real range of values without inventing thresholds',
      () => {
        render(
          <SensorTrendChart
            readings={[
              createReading(
                'reading-1',
                '2026-09-06T08:00:00Z',
                6.8,
              ),

              createReading(
                'reading-2',
                '2026-09-06T08:01:00Z',
                7.3,
              ),
            ]}
            unit="pH"
          />,
        )


        expect(
          screen.getByText(
            'Range: 6.8 – 7.3 pH',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'ignores invalid timestamps instead of plotting misleading data',
      () => {
        render(
          <SensorTrendChart
            readings={[
              createReading(
                'reading-invalid',
                'not-a-date',
                10,
              ),

              createReading(
                'reading-1',
                '2026-09-06T08:00:00Z',
                7,
              ),
            ]}
            unit="pH"
          />,
        )


        expect(
          screen.getByText(
            'Not enough readings for a trend',
          ),
        ).toBeInTheDocument()
      },
    )
  },
)