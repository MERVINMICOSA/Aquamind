import {
  fireEvent,
  render,
  screen,
} from '@testing-library/react'

import {
  MemoryRouter,
  Route,
  Routes,
} from 'react-router-dom'

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
  useSensorDetail,
} from '../hooks/useSensorDetail'

import {
  SensorDetailPage,
} from './SensorDetailPage'


vi.mock(
  '../hooks/useSensorDetail',
  () => ({
    useSensorDetail:
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
  '../components/sensors/SensorCalibrationPanel',
  () => ({
    SensorCalibrationPanel: ({
      sensorId,
      calibrationStatus,
    }: {
      sensorId: string
      calibrationStatus: string
    }) => (
      <div data-testid="calibration-panel">
        Calibration for {sensorId}: {calibrationStatus}
      </div>
    ),
  }),
)


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
    'SIM-PH-001',

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


const READING = {
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
}


function renderPage() {
  render(
    <MemoryRouter
      initialEntries={[
        '/sensors/sensor-1',
      ]}
    >
      <Routes>
        <Route
          path="/sensors/:sensorId"
          element={
            <SensorDetailPage />
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}


describe(
  'AquaMind sensor detail page',
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
      'shows a loading state while the sensor is loading',
      () => {
        vi.mocked(
          useSensorDetail,
        ).mockReturnValue({
          sensor:
            null,

          latestReading:
            null,

          readings: [],

          sensorStatus:
            'loading',

          historyStatus:
            'idle',

          sensorErrorMessage:
            null,

          historyErrorMessage:
            null,

          hasNext:
            false,

          hasPrevious:
            false,

          offset:
            0,

          pageNumber:
            1,

          nextPage:
            vi.fn(),

          previousPage:
            vi.fn(),
        })


        renderPage()


        expect(
          screen.getByText(
            'Loading sensor...',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'renders sensor configuration and the latest persisted reading',
      () => {
        vi.mocked(
          useSensorDetail,
        ).mockReturnValue({
          sensor:
            SENSOR,

          latestReading:
            READING,

          readings: [
            READING,
          ],

          sensorStatus:
            'ready',

          historyStatus:
            'ready',

          sensorErrorMessage:
            null,

          historyErrorMessage:
            null,

          hasNext:
            false,

          hasPrevious:
            false,

          offset:
            0,

          pageNumber:
            1,

          nextPage:
            vi.fn(),

          previousPage:
            vi.fn(),
        })


        renderPage()


        expect(
          screen.getByRole(
            'heading',
            {
              name:
                'Tank pH Sensor',
            },
          ),
        ).toBeInTheDocument()


        expect(
          screen.getAllByText(
            '7.1',
          ).length,
        ).toBeGreaterThan(
          0,
        )


        expect(
          screen.getByText(
            'On time',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getAllByText(
            'simulator',
          ).length,
        ).toBeGreaterThan(
          0,
        )


        expect(
          screen.getByText(
            'SIM-PH-001',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByRole('heading', { name: 'What this sensor page shows' }),
        ).toBeInTheDocument()

        expect(
          screen.getByTestId('calibration-panel'),
        ).toHaveTextContent('sensor-1: pending')

        expect(
          screen.getByText(/Calibration required: this/),
        ).toHaveTextContent('must not')
      },
    )


    it(
      'shows an honest no-reading state',
      () => {
        vi.mocked(
          useSensorDetail,
        ).mockReturnValue({
          sensor:
            SENSOR,

          latestReading:
            null,

          readings: [],

          sensorStatus:
            'ready',

          historyStatus:
            'ready',

          sensorErrorMessage:
            null,

          historyErrorMessage:
            null,

          hasNext:
            false,

          hasPrevious:
            false,

          offset:
            0,

          pageNumber:
            1,

          nextPage:
            vi.fn(),

          previousPage:
            vi.fn(),
        })


        renderPage()


        expect(
          screen.getByText(
            'No reading yet',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByText(
            'No readings on this page',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'uses the supplied pagination actions',
      () => {
        const nextPage =
          vi.fn()

        const previousPage =
          vi.fn()


        vi.mocked(
          useSensorDetail,
        ).mockReturnValue({
          sensor:
            SENSOR,

          latestReading:
            READING,

          readings: [
            READING,
          ],

          sensorStatus:
            'ready',

          historyStatus:
            'ready',

          sensorErrorMessage:
            null,

          historyErrorMessage:
            null,

          hasNext:
            true,

          hasPrevious:
            true,

          offset:
            50,

          pageNumber:
            2,

          nextPage,

          previousPage,
        })


        renderPage()


        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Previous',
            },
          ),
        )


        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Next',
            },
          ),
        )


        expect(
          previousPage,
        ).toHaveBeenCalledTimes(
          1,
        )


        expect(
          nextPage,
        ).toHaveBeenCalledTimes(
          1,
        )


        expect(
          screen.getByText(
            'Page 2',
          ),
        ).toBeInTheDocument()
      },
    )
  },
)