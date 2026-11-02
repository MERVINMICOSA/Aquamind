import {
  render,
  screen,
} from '@testing-library/react'
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  useDashboardOverview,
} from '../hooks/useDashboardOverview'

import {
  useDashboardSensorTrend,
} from '../hooks/useDashboardSensorTrend'

import {
  useDashboardActuatorActivity,
} from '../hooks/useDashboardActuatorActivity'

import {
  DashboardPage,
} from './DashboardPage'


vi.mock(
  '../hooks/useDashboardOverview',
  () => ({
    useDashboardOverview:
      vi.fn(),
  }),
)


vi.mock(
  '../hooks/useDashboardSensorTrend',
  () => ({
    useDashboardSensorTrend:
      vi.fn(),
  }),
)


vi.mock(
  '../hooks/useDashboardActuatorActivity',
  () => ({
    useDashboardActuatorActivity:
      vi.fn(),
  }),
)


const SYSTEM = {
  id: 'system-1',
  name: 'Main System',
  description: null,
  timezone: 'UTC',
  is_active: true,
  created_at:
    '2026-09-06T00:00:00Z',
  updated_at:
    '2026-09-06T00:00:00Z',
}


const WATER_TEMPERATURE_SENSOR = {
  id: 'sensor-1',
  system_id: 'system-1',
  name: 'Water Temperature',

  sensor_type:
    'water_temperature',

  measurement_type:
    'temperature',

  location_type:
    'tank',

  location_id:
    null,

  unit:
    'C',

  hardware_identifier:
    null,

  is_simulated:
    false,

  is_enabled:
    true,

  sampling_interval_seconds:
    30,

  calibration_status:
    'pending',

  created_at:
    '2026-09-06T00:00:00Z',

  updated_at:
    '2026-09-06T00:00:00Z',
}


describe(
  'AquaMind dashboard',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()

      vi.mocked(
        useDashboardSensorTrend,
      ).mockReturnValue({
        readings: [],
        status: 'ready',
        errorMessage: null,
      })

      vi.mocked(
        useDashboardActuatorActivity,
      ).mockReturnValue({
        events: [],
        status: 'idle',
        errorMessage: null,
      })
    })


    it(
      'shows an honest empty state when no aquaponics systems exist',
      () => {
        vi.mocked(
          useDashboardOverview,
        ).mockReturnValue({
          systems: [],

          selectedSystem:
            null,

          selectedSystemId:
            null,

          sensors: [],
          actuators: [],
          alerts: [],
          latestReadings: [],

          systemsStatus:
            'ready',

          overviewStatus:
            'idle',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })

        render(
          <DashboardPage />,
        )

        expect(
          screen.getByRole(
            'heading',
            {
              name:
                'No aquaponics system configured',
            },
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'renders real resource counts for the selected system',
      () => {
        vi.mocked(
          useDashboardOverview,
        ).mockReturnValue({
          systems: [
            SYSTEM,
          ],

          selectedSystem:
            SYSTEM,

          selectedSystemId:
            'system-1',

          sensors: [
            WATER_TEMPERATURE_SENSOR,
          ],

          actuators: [],

          alerts: [],

          latestReadings: [],

          systemsStatus:
            'ready',

          overviewStatus:
            'ready',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })

        render(
          <DashboardPage />,
        )

        expect(
          screen.getByText(
            'Main System',
            {
              selector: 'strong',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'Sensors',
            {
              selector: 'dt',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'Actuators',
            {
              selector: 'dt',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'Alert records',
            {
              selector: 'dt',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'of 1 enabled',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'of 0 enabled',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'for this system',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'shows no reading yet for a configured sensor without telemetry',
      () => {
        vi.mocked(
          useDashboardOverview,
        ).mockReturnValue({
          systems: [
            SYSTEM,
          ],

          selectedSystem:
            SYSTEM,

          selectedSystemId:
            'system-1',

          sensors: [
            WATER_TEMPERATURE_SENSOR,
          ],

          actuators: [],
          alerts: [],
          latestReadings: [],

          systemsStatus:
            'ready',

          overviewStatus:
            'ready',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })

        render(
          <DashboardPage />,
        )

        expect(
          screen.getByText(
            'No reading yet',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'Waiting for the first persisted sensor reading.',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            '0 of 1 reporting',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'renders the real latest reading for a configured sensor',
      () => {
        vi.mocked(
          useDashboardOverview,
        ).mockReturnValue({
          systems: [
            SYSTEM,
          ],

          selectedSystem:
            SYSTEM,

          selectedSystemId:
            'system-1',

          sensors: [
            {
              ...WATER_TEMPERATURE_SENSOR,

              calibration_status:
                'verified',
            },
          ],

          actuators: [],
          alerts: [],

          latestReadings: [
            {
              id:
                'reading-1',

              sensor_id:
                'sensor-1',

              recorded_at:
                '2026-09-06T06:00:00Z',

              value_numeric:
                26.4,

              unit:
                'C',

              quality_status:
                'good',

              source:
                'hardware',

              sequence_number:
                1,

              created_at:
                '2026-09-06T06:00:01Z',
            },
          ],

          systemsStatus:
            'ready',

          overviewStatus:
            'ready',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })

        render(
          <DashboardPage />,
        )

        expect(
          screen.getByRole(
            'heading',
            {
              name: 'Water Temperature',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            '26.4',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            '1 of 1 reporting',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'good',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'hardware',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByRole(
            'heading',
            {
              name: 'Sensor trends',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByLabelText(
            'Trend sensor',
          ),
        ).toHaveValue(
          'sensor-1',
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