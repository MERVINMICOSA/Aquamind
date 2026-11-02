import { MemoryRouter } from 'react-router-dom'
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
  useActuatorsOverview,
} from '../hooks/useActuatorsOverview'

import {
  ActuatorsPage,
} from './ActuatorsPage'


vi.mock(
  '../hooks/useActuatorsOverview',
  () => ({
    useActuatorsOverview:
      vi.fn(),
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


const ACTUATOR = {
  id:
    'actuator-1',

  system_id:
    'system-1',

  name:
    'Circulation Pump',

  actuator_type:
    'pump',

  control_mode:
    'automatic',

  hardware_identifier:
    'SIM-PUMP-001',

  location_type:
    'tank',

  location_id:
    null,

  is_enabled:
    true,

  safety_config:
    null,

  current_state:
    'off',

  current_value:
    null,

  last_state_at:
    null,

  created_at:
    '2026-09-06T00:00:00Z',

  updated_at:
    '2026-09-06T00:00:00Z',

  deleted_at:
    null,
}


describe(
  'AquaMind actuators page',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })


    it(
      'shows an honest empty state when no system exists',
      () => {
        vi.mocked(
          useActuatorsOverview,
        ).mockReturnValue({
          systems: [],

          selectedSystem:
            null,

          selectedSystemId:
            null,

          actuators: [],

          systemsStatus:
            'ready',

          actuatorsStatus:
            'idle',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })


        render(
          <MemoryRouter><ActuatorsPage /></MemoryRouter>,
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
      'does not treat an untimestamped default state as recorded actuator activity',
      () => {
        vi.mocked(
          useActuatorsOverview,
        ).mockReturnValue({
          systems: [
            SYSTEM,
          ],

          selectedSystem:
            SYSTEM,

          selectedSystemId:
            'system-1',

          actuators: [
            ACTUATOR,
          ],

          systemsStatus:
            'ready',

          actuatorsStatus:
            'ready',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })


        render(
          <MemoryRouter><ActuatorsPage /></MemoryRouter>,
        )


        expect(
          screen.getByText(
            'Circulation Pump',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByText(
            'No state recorded',
          ),
        ).toBeInTheDocument()


        expect(screen.getByRole('link', { name: 'Circulation Pump' }))
          .toHaveAttribute('href', '/actuators/actuator-1')

        expect(
          screen.getByText(
            'SIM-PUMP-001',
          ),
        ).toBeInTheDocument()


        expect(
          screen.getByText(
            'Configuration and persisted state do not confirm that physical hardware is currently connected or energized.',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'shows a timestamped persisted actuator state when one exists',
      () => {
        vi.mocked(
          useActuatorsOverview,
        ).mockReturnValue({
          systems: [
            SYSTEM,
          ],

          selectedSystem:
            SYSTEM,

          selectedSystemId:
            'system-1',

          actuators: [
            {
              ...ACTUATOR,

              current_state:
                'on',

              current_value:
                1,

              last_state_at:
                '2026-09-06T08:00:00Z',

              safety_config: {
                max_runtime_seconds:
                  300,
              },
            },
          ],

          systemsStatus:
            'ready',

          actuatorsStatus:
            'ready',

          errorMessage:
            null,

          selectSystem:
            vi.fn(),
        })


        render(
          <MemoryRouter><ActuatorsPage /></MemoryRouter>,
        )


        expect(
          screen.getByText(
            'on',
          ),
        ).toBeInTheDocument()


        expect(
            screen.getByText(
                'Configured',
                {
                selector: 'dd',
                },
            ),
        ).toBeInTheDocument()


        expect(
            screen.getByText(
                '1',
                {
                selector: 'dd',
                },
            ),
        ).toBeInTheDocument()
      },
    )
  },
)
