import {
  fireEvent,
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
  useRefillOverview,
} from '../hooks/useRefillOverview'

import type {
  RefillEvent,
  Reservoir,
} from '../types/refill'

import type {
  Tank,
} from '../types/tank'

import {
  RefillPage,
} from './RefillPage'


vi.mock(
  '../hooks/useRefillOverview',
  () => ({
    useRefillOverview:
      vi.fn(),
  }),
)


const mockedUseRefillOverview =
  vi.mocked(
    useRefillOverview,
  )


const selectSystem =
  vi.fn()

const selectReservoir =
  vi.fn()

const nextPage =
  vi.fn()

const previousPage =
  vi.fn()


const system = {
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
    '2026-09-20T00:00:00Z',

  updated_at:
    '2026-09-20T00:00:00Z',
}


const reservoir:
  Reservoir = {
    id:
      'reservoir-1',

    system_id:
      system.id,

    name:
      'Main Reservoir',

    capacity_liters:
      1000,

    is_active:
      true,

    created_at:
      '2026-09-20T00:00:00Z',

    updated_at:
      '2026-09-20T00:00:00Z',
  }


const tank:
  Tank = {
    id:
      'tank-1',

    system_id:
      system.id,

    name:
      'Fish Tank',

    capacity_liters:
      500,

    species:
      null,

    is_active:
      true,

    created_at:
      '2026-09-20T00:00:00Z',

    updated_at:
      '2026-09-20T00:00:00Z',
  }


const refillEvent:
  RefillEvent = {
    id:
      'refill-event-1',

    reservoir_id:
      reservoir.id,

    target_tank_id:
      tank.id,

    start_level_percent:
      0,

    end_level_percent:
      40,

    started_at:
      '2026-09-20T01:00:00Z',

    completed_at:
      null,

    duration_seconds:
      0,

    trigger:
      'automatic',

    status:
      'running',

    timeout_reason:
      null,

    created_at:
      '2026-09-20T01:00:00Z',
  }


function readyOverview():
  ReturnType<
    typeof useRefillOverview
  > {
  return {
    systems: [
      system,
    ],

    systemsStatus:
      'ready',

    selectedSystemId:
      system.id,

    selectedSystem:
      system,

    reservoirs: [
      reservoir,
    ],

    tanks: [
      tank,
    ],

    resourcesStatus:
      'ready',

    selectedReservoirId:
      reservoir.id,

    selectedReservoir:
      reservoir,

    refillEvents: [
      refillEvent,
    ],

    historyStatus:
      'ready',

    historyOffset:
      0,

    pageNumber:
      1,

    hasNextPage:
      false,

    hasPreviousPage:
      false,

    selectSystem,
    selectReservoir,
    nextPage,
    previousPage,
  }
}


beforeEach(
  () => {
    selectSystem.mockReset()
    selectReservoir.mockReset()
    nextPage.mockReset()
    previousPage.mockReset()

    mockedUseRefillOverview
      .mockReset()

    mockedUseRefillOverview
      .mockReturnValue(
        readyOverview(),
      )
  },
)


describe(
  'RefillPage',
  () => {
    it(
      'renders persisted refill history without execution controls',
      () => {
        render(
          <RefillPage />,
        )

        expect(
          screen.getByText(
            /Target tank:\s*Fish Tank/,
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            /Start level:\s*0%/,
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            /Duration:\s*0 s/,
          ),
        ).toBeInTheDocument()

        expect(
          screen.getAllByText(
            /Not recorded/,
          ),
        ).toHaveLength(
          2,
        )
        expect(
          screen.getByText(
            /do not establish that physical hardware executed a refill/i,
          ),
        ).toBeInTheDocument()

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                /start refill/i,
            },
          ),
        ).not.toBeInTheDocument()

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                /stop refill/i,
            },
          ),
        ).not.toBeInTheDocument()

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                /delete/i,
            },
          ),
        ).not.toBeInTheDocument()
      },
    )


    it(
      'changes system and reservoir through the overview hook',
      () => {
        mockedUseRefillOverview
          .mockReturnValue({
            ...readyOverview(),

            systems: [
              system,

              {
                ...system,

                id:
                  'system-2',

                name:
                  'Second System',
              },
            ],

            reservoirs: [
              reservoir,

              {
                ...reservoir,

                id:
                  'reservoir-2',

                name:
                  'Second Reservoir',
              },
            ],
          })

        render(
          <RefillPage />,
        )

        fireEvent.change(
          screen.getByLabelText(
            'Aquaponics system',
          ),
          {
            target: {
              value:
                'system-2',
            },
          },
        )

        expect(
          selectSystem,
        ).toHaveBeenCalledWith(
          'system-2',
        )

        fireEvent.change(
          screen.getByLabelText(
            'Reservoir',
          ),
          {
            target: {
              value:
                'reservoir-2',
            },
          },
        )

        expect(
          selectReservoir,
        ).toHaveBeenCalledWith(
          'reservoir-2',
        )
      },
    )


    it(
      'uses the supplied bounded history pagination actions',
      () => {
        mockedUseRefillOverview
          .mockReturnValue({
            ...readyOverview(),

            historyOffset:
              50,

            pageNumber:
              2,

            hasNextPage:
              true,

            hasPreviousPage:
              true,
          })

        render(
          <RefillPage />,
        )

        expect(
          screen.getByText(
            'Page 2',
          ),
        ).toBeInTheDocument()

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
      },
    )


    it(
      'shows an honest empty state when no system exists',
      () => {
        mockedUseRefillOverview
          .mockReturnValue({
            ...readyOverview(),

            systems:
              [],

            selectedSystemId:
              null,

            selectedSystem:
              null,

            reservoirs:
              [],

            tanks:
              [],

            selectedReservoirId:
              null,

            selectedReservoir:
              null,

            refillEvents:
              [],
          })

        render(
          <RefillPage />,
        )

        expect(
          screen.getByText(
            'No aquaponics system configured',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'shows an honest empty state when the system has no reservoir',
      () => {
        mockedUseRefillOverview
          .mockReturnValue({
            ...readyOverview(),

            reservoirs:
              [],

            selectedReservoirId:
              null,

            selectedReservoir:
              null,

            refillEvents:
              [],
          })

        render(
          <RefillPage />,
        )

        expect(
          screen.getByText(
            'No reservoirs configured',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'shows an honest empty state when the reservoir has no refill history',
      () => {
        mockedUseRefillOverview
          .mockReturnValue({
            ...readyOverview(),

            refillEvents:
              [],
          })

        render(
          <RefillPage />,
        )

        expect(
          screen.getByText(
            'No refill events recorded for this reservoir.',
          ),
        ).toBeInTheDocument()
      },
    )
  },
)