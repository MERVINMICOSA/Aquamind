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
  useCurrentTime,
} from '../hooks/useCurrentTime'

import {
  useSensorsOverview,
} from '../hooks/useSensorsOverview'

import {
  SensorsPage,
} from './SensorsPage'

import {
  MemoryRouter,
} from 'react-router-dom'

function renderSensorsPage() {
  render(
    <MemoryRouter>
      <SensorsPage />
    </MemoryRouter>,
  )
}


vi.mock(
  '../hooks/useSensorsOverview',
  () => ({
    useSensorsOverview:
      vi.fn(),
  }),
)


vi.mock(
  '../hooks/useCurrentTime',
  () => ({
    useCurrentTime:
      vi.fn(),
  }),
)


vi.mock(
  '../components/dashboard/Esp32TelemetryPanel',
  () => ({
    Esp32TelemetryPanel:
      ({ systemId }: { systemId: string }) => (
        <div data-testid="esp32-telemetry">
          ESP32 telemetry for {systemId}
        </div>
      ),
  }),
)


const SYSTEM = {
  id:
    'system-1',

  name:
    'Main System',

  description:
    null,

  timezone:
    'UTC',

  is_active:
    true,

  created_at:
    '2026-09-06T00:00:00Z',

  updated_at:
    '2026-09-06T00:00:00Z',
}


const SENSOR = {
  id:
    'sensor-1',

  system_id:
    'system-1',

  name:
    'Tank pH Sensor',

  sensor_type:
    'ph',

  measurement_type:
    'ph',

  location_type:
    'tank',

  location_id:
    null,

  unit:
    'pH',

  hardware_identifier:
    null,

  is_simulated:
    true,

  is_enabled:
    true,

  sampling_interval_seconds:
    60,

  calibration_status:
    'pending',

  created_at:
    '2026-09-06T00:00:00Z',

  updated_at:
    '2026-09-06T00:00:00Z',
}


describe(
  'AquaMind sensors page',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()

      vi.mocked(
        useCurrentTime,
      ).mockReturnValue(
        Date.parse(
          '2026-09-06T08:00:00Z',
        ),
      )
    })


    it(
      'shows an honest empty state when no system exists',
      () => {
        vi.mocked(
          useSensorsOverview,
        ).mockReturnValue({
          systems: [],

          selectedSystem:
            null,

          selectedSystemId:
            null,

          sensors: [],

          latestReadings: [],

          systemsStatus:
            'ready',

          sensorsStatus:
            'idle',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })


        renderSensorsPage()


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
      'shows configured sensors without inventing telemetry',
      () => {
        vi.mocked(
          useSensorsOverview,
        ).mockReturnValue({
          systems: [
            SYSTEM,
          ],

          selectedSystem:
            SYSTEM,

          selectedSystemId:
            'system-1',

          sensors: [
            SENSOR,
          ],

          latestReadings: [],

          systemsStatus:
            'ready',

          sensorsStatus:
            'ready',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })


        renderSensorsPage()


        expect(
          screen.getByText(
            'Tank pH Sensor',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByText(
            'No reading yet',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByText(
            'Yes',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'does not count stale saved telemetry as on-time reporting',
      () => {
        vi.mocked(
          useSensorsOverview,
        ).mockReturnValue({
          systems: [SYSTEM],
          selectedSystem: SYSTEM,
          selectedSystemId: 'system-1',
          sensors: [SENSOR],
          latestReadings: [
            {
              id: 'old-reading',
              sensor_id: 'sensor-1',
              recorded_at: '2026-09-06T06:00:00Z',
              value_numeric: 7.1,
              unit: 'pH',
              quality_status: 'good',
              source: 'hardware',
              sequence_number: 1,
              created_at: '2026-09-06T06:00:01Z',
            },
          ],
          systemsStatus: 'ready',
          sensorsStatus: 'ready',
          errorMessage: null,
          selectSystem: vi.fn(),
        })

        renderSensorsPage()

        expect(
          screen.getByText('Needs review').parentElement,
        ).toHaveTextContent('1')

        expect(
          screen.getByText('On time').parentElement,
        ).toHaveTextContent('0')

        expect(
          screen.getByTestId('esp32-telemetry'),
        ).toHaveTextContent('system-1')

        expect(
          screen.getByText(/Receiving a packet does not automatically/),
        ).toBeInTheDocument()
      },
    )


    it(
      'renders the latest persisted reading and timing state',
      () => {
        vi.mocked(
          useSensorsOverview,
        ).mockReturnValue({
          systems: [
            SYSTEM,
          ],

          selectedSystem:
            SYSTEM,

          selectedSystemId:
            'system-1',

          sensors: [
            SENSOR,
          ],

          latestReadings: [
            {
              id:
                'reading-1',

              sensor_id:
                'sensor-1',

              recorded_at:
                '2026-09-06T07:59:30Z',

              value_numeric:
                7.1,

              unit:
                'pH',

              quality_status:
                'good',

              source:
                'simulator',

              sequence_number:
                1,

              created_at:
                '2026-09-06T07:59:31Z',
            },
          ],

          systemsStatus:
            'ready',

          sensorsStatus:
            'ready',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })


        renderSensorsPage()


        expect(
          screen.getByText(
            '7.1',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByText(
            'On time',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByText(
            'simulator',
          ),
        ).toBeInTheDocument()
      },
    )
  },
)