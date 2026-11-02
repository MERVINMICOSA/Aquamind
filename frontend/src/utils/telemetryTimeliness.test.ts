import {
  describe,
  expect,
  it,
} from 'vitest'

import {
  getTelemetryTimeliness,
} from './telemetryTimeliness'


const NOW =
  Date.parse(
    '2026-09-06T08:00:00Z',
  )


describe(
  'telemetry timeliness',
  () => {
    it(
      'reports a reading as on time while it is within the configured sampling interval',
      () => {
        expect(
          getTelemetryTimeliness(
            '2026-09-06T07:59:40Z',
            30,
            NOW,
          ),
        ).toEqual({
          status:
            'on_time',

          ageSeconds:
            20,
        })
      },
    )


    it(
      'reports a reading as late after the configured sampling interval has elapsed',
      () => {
        expect(
          getTelemetryTimeliness(
            '2026-09-06T07:59:29Z',
            30,
            NOW,
          ),
        ).toEqual({
          status:
            'late',

          ageSeconds:
            31,
        })
      },
    )


    it(
      'treats the exact sampling interval boundary as on time',
      () => {
        expect(
          getTelemetryTimeliness(
            '2026-09-06T07:59:30Z',
            30,
            NOW,
          ),
        ).toEqual({
          status:
            'on_time',

          ageSeconds:
            30,
        })
      },
    )


    it(
      'reports an invalid timestamp as unknown',
      () => {
        expect(
          getTelemetryTimeliness(
            'invalid-timestamp',
            30,
            NOW,
          ),
        ).toEqual({
          status:
            'unknown',

          ageSeconds:
            null,
        })
      },
    )


    it(
      'reports a future timestamp as unknown',
      () => {
        expect(
          getTelemetryTimeliness(
            '2026-09-06T08:01:00Z',
            30,
            NOW,
          ),
        ).toEqual({
          status:
            'unknown',

          ageSeconds:
            null,
        })
      },
    )


    it(
      'reports an invalid sampling interval as unknown',
      () => {
        expect(
          getTelemetryTimeliness(
            '2026-09-06T07:59:50Z',
            0,
            NOW,
          ),
        ).toEqual({
          status:
            'unknown',

          ageSeconds:
            null,
        })
      },
    )
  },
)