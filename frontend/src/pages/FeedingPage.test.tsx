import {
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'

import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  useAuth,
} from '../hooks/useAuth'

import {
  useFeedingOverview,
} from '../hooks/useFeedingOverview'

import type {
  FeederCalibration,
  FeederCalibrationInput,
  FeederCalibrationUpdateInput,
  FeedingSchedule,
  FeedingScheduleInput,
  FeedingScheduleUpdateInput,
  FishPopulationInput,
  FishPopulationRecord,
  FishPopulationUpdateInput,
} from '../types/feeding'

import {
  FeedingPage,
} from './FeedingPage'


vi.mock(
  '../hooks/useAuth',
  () => ({
    useAuth:
      vi.fn(),
  }),
)


vi.mock(
  '../hooks/useFeedingOverview',
  () => ({
    useFeedingOverview:
      vi.fn(),
  }),
)


const mockedUseAuth =
  vi.mocked(
    useAuth,
  )


const mockedUseFeedingOverview =
  vi.mocked(
    useFeedingOverview,
  )


const selectSystem =
  vi.fn()

const nextPage =
  vi.fn()

const previousPage =
  vi.fn()


const selectCalibrationActuator =
  vi.fn()

const nextCalibrationPage =
  vi.fn()

const previousCalibrationPage =
  vi.fn()


const selectPopulationTank =
  vi.fn()

const nextPopulationPage =
  vi.fn()

const previousPopulationPage =
  vi.fn()


const login =
  vi.fn(
    async () => {
      return undefined
    },
  )

const logout =
  vi.fn(
    async () => {
      return undefined
    },
  )


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
    '2026-09-08T00:00:00Z',

  updated_at:
    '2026-09-08T00:00:00Z',
}


const tank = {
  id:
    'tank-1',

  system_id:
    system.id,

  name:
    'Main Fish Tank',

  capacity_liters:
    1000,

  species:
    'Tilapia',

  is_active:
    true,

  created_at:
    '2026-09-08T00:00:00Z',

  updated_at:
    '2026-09-08T00:00:00Z',
}


const actuator = {
  id:
    'actuator-1',

  system_id:
    system.id,

  name:
    'Feeding Actuator',

  actuator_type:
    'water pump',

  control_mode:
    'scheduled',

  hardware_identifier:
    'FEEDING-ACTUATOR-001',

  location_type:
    'tank',

  location_id:
    tank.id,

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
    '2026-09-08T00:00:00Z',

  updated_at:
    '2026-09-08T00:00:00Z',

  deleted_at:
    null,
}


const schedule:
  FeedingSchedule = {
    id:
      'schedule-1',

    system_id:
      system.id,

    actuator_id:
      actuator.id,

    name:
      'Morning Feeding',

    schedule_expression:
      '0 8 * * *',

    enabled:
      true,

    max_per_feed_grams:
      100,

    created_at:
      '2026-09-08T00:00:00Z',

    updated_at:
      '2026-09-08T00:00:00Z',
  }


const calibration:
  FeederCalibration = {
    id:
      'calibration-1',

    actuator_id:
      actuator.id,

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
      '2026-09-08T02:00:00Z',

    verified_by_user_id:
      null,

    notes:
      null,
  }


const populationRecord:
  FishPopulationRecord = {
    id:
      'population-1',

    tank_id:
      tank.id,

    species:
      'Tilapia',

    count:
      100,

    estimated_biomass_grams:
      25000,

    effective_at:
      '2026-09-08T03:00:00Z',

    recorded_by_user_id:
      'admin-user',

    notes:
      null,
  }


const createSchedule =
  vi.fn(
    async (
      input:
        FeedingScheduleInput,
    ): Promise<FeedingSchedule> => {
      void input

      return schedule
    },
  )


const updateSchedule =
  vi.fn(
    async (
      scheduleId: string,
      input:
        FeedingScheduleUpdateInput,
    ): Promise<FeedingSchedule> => {
      void scheduleId
      void input

      return schedule
    },
  )


const deleteSchedule =
  vi.fn(
    async (
      scheduleId: string,
    ): Promise<void> => {
      void scheduleId
    },
  )


const createCalibration =
  vi.fn(
    async (
      input:
        FeederCalibrationInput,
    ): Promise<FeederCalibration> => {
      void input

      return calibration
    },
  )


const updateCalibration =
  vi.fn(
    async (
      calibrationId: string,
      input:
        FeederCalibrationUpdateInput,
    ): Promise<FeederCalibration> => {
      void calibrationId
      void input

      return calibration
    },
  )


const deleteCalibration =
  vi.fn(
    async (
      calibrationId: string,
    ): Promise<void> => {
      void calibrationId
    },
  )


const createPopulationRecord =
  vi.fn(
    async (
      input:
        FishPopulationInput,
    ): Promise<FishPopulationRecord> => {
      void input

      return populationRecord
    },
  )


const updatePopulationRecord =
  vi.fn(
    async (
      recordId: string,
      input:
        FishPopulationUpdateInput,
    ): Promise<FishPopulationRecord> => {
      void recordId
      void input

      return populationRecord
    },
  )


const deletePopulationRecord =
  vi.fn(
    async (
      recordId: string,
    ): Promise<void> => {
      void recordId
    },
  )


function adminAuth():
  ReturnType<typeof useAuth> {
  return {
    status:
      'authenticated',

    user: {
      userId:
        'admin-user',

      username:
        'admin',

      role:
        'admin',

      isActive:
        true,
    },

    isAuthenticated:
      true,

    login,

    logout,
  }
}


function readyOverview():
  ReturnType<typeof useFeedingOverview> {
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

    actuators: [
      actuator,
    ],

    actuatorStatus:
      'ready',

    selectedCalibrationActuatorId:
      actuator.id,

    selectedCalibrationActuator:
      actuator,

    calibrations:
      [],

    calibrationStatus:
      'ready',

    calibrationHasNext:
      false,

    calibrationHasPrevious:
      false,

    calibrationPageNumber:
      1,

    tanks: [
      tank,
    ],

    tankStatus:
      'ready',

    selectedPopulationTankId:
      tank.id,

    selectedPopulationTank:
      tank,

    populationRecords:
      [],

    populationStatus:
      'ready',

    populationHasNext:
      false,

    populationHasPrevious:
      false,

    populationPageNumber:
      1,

    schedules: [
      schedule,
    ],

    scheduleStatus:
      'ready',

    events: [
      {
        id:
          'event-1',

        schedule_id:
          null,

        actuator_event_id:
          'actuator-event-1',

        tank_id:
          tank.id,

        amount_grams:
          0,

        duration_seconds:
          10,

        calculated_from_biomass:
          0,

        calibration_id:
          null,

        executed_at:
          '2026-09-08T01:00:00Z',

        status:
          'completed',

        notes:
          null,
      },
    ],

    historyStatus:
      'ready',

    mutationStatus:
      'idle',

    mutationError:
      null,

    isMutating:
      false,

    hasNext:
      false,

    hasPrevious:
      false,

    pageNumber:
      1,

    createSchedule,
    updateSchedule,
    deleteSchedule,

    createCalibration,
    updateCalibration,
    deleteCalibration,

    createPopulationRecord,
    updatePopulationRecord,
    deletePopulationRecord,

    selectSystem,

    selectCalibrationActuator,
    nextCalibrationPage,
    previousCalibrationPage,

    selectPopulationTank,
    nextPopulationPage,
    previousPopulationPage,

    nextPage,
    previousPage,
  }
}


describe(
  'AquaMind feeding page',
  () => {
    beforeEach(() => {
      mockedUseAuth
        .mockReset()

      mockedUseFeedingOverview
        .mockReset()

      selectSystem
        .mockReset()

      nextPage
        .mockReset()

      previousPage
        .mockReset()

      createSchedule
        .mockClear()

      updateSchedule
        .mockClear()

      deleteSchedule
        .mockClear()

      createCalibration
        .mockClear()

      updateCalibration
        .mockClear()

      deleteCalibration
        .mockClear()

      selectCalibrationActuator
        .mockReset()

      nextCalibrationPage
        .mockReset()

      previousCalibrationPage
        .mockReset()

      createPopulationRecord
        .mockClear()

      updatePopulationRecord
        .mockClear()

      deletePopulationRecord
        .mockClear()

      selectPopulationTank
        .mockReset()

      nextPopulationPage
        .mockReset()

      previousPopulationPage
        .mockReset()

      login
        .mockClear()

      logout
        .mockClear()

      mockedUseAuth
        .mockReturnValue(
          adminAuth(),
        )
    })


    it(
      'shows an honest empty state when no system exists',
      () => {
        mockedUseFeedingOverview
          .mockReturnValue({
            ...readyOverview(),

            systems:
              [],

            selectedSystemId:
              null,

            selectedSystem:
              null,

            actuators:
              [],

            selectedCalibrationActuatorId:
              null,

            selectedCalibrationActuator:
              null,

            calibrations:
              [],

            tanks:
              [],

            selectedPopulationTankId:
              null,

            selectedPopulationTank:
              null,

            populationRecords:
              [],

            schedules:
              [],

            events:
              [],
          })

        render(
          <FeedingPage />,
        )

        expect(
          screen.getByText(
            'No aquaponics system configured',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'renders schedule configuration and persisted feeding history',
      () => {
        mockedUseFeedingOverview
          .mockReturnValue(
            readyOverview(),
          )

        render(
          <FeedingPage />,
        )

        expect(
          screen.getByText(
            'Morning Feeding',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            '0 8 * * *',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'Persisted feeding event history',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'actuator-event-1',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'tank-1',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'preserves zero values and renders nullable event metadata honestly',
      () => {
        mockedUseFeedingOverview
          .mockReturnValue(
            readyOverview(),
          )

        render(
          <FeedingPage />,
        )

        expect(
          screen.getAllByText(
            '0',
          ).length,
        ).toBeGreaterThanOrEqual(
          2,
        )

        expect(
          screen.getAllByText(
            'Not recorded',
          ).length,
        ).toBeGreaterThanOrEqual(
          3,
        )
      },
    )


    it(
      'changes systems through the overview hook without exposing execution controls',
      () => {
        mockedUseFeedingOverview
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
          })

        render(
          <FeedingPage />,
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

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                /feed now|calibrate/i,
            },
          ),
        ).not.toBeInTheDocument()
      },
    )


    it(
      'creates a feeding schedule from the real backend fields',
      async () => {
        mockedUseFeedingOverview
          .mockReturnValue(
            readyOverview(),
          )

        render(
          <FeedingPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Add schedule',
            },
          ),
        )

        fireEvent.change(
          screen.getByLabelText(
            'Name',
          ),
          {
            target: {
              value:
                'Evening Feeding',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Schedule expression',
          ),
          {
            target: {
              value:
                '0 18 * * *',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Max per feed (grams)',
          ),
          {
            target: {
              value:
                '75',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save schedule',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              createSchedule,
            ).toHaveBeenCalledWith({
              actuator_id:
                actuator.id,

              name:
                'Evening Feeding',

              schedule_expression:
                '0 18 * * *',

              enabled:
                true,

              max_per_feed_grams:
                75,
            })
          },
        )
      },
    )


    it(
      'updates only changed schedule fields',
      async () => {
        mockedUseFeedingOverview
          .mockReturnValue(
            readyOverview(),
          )

        render(
          <FeedingPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Edit',
            },
          ),
        )

        fireEvent.change(
          screen.getByLabelText(
            'Name',
          ),
          {
            target: {
              value:
                'Updated Morning Feeding',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save schedule',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              updateSchedule,
            ).toHaveBeenCalledWith(
              schedule.id,
              {
                name:
                  'Updated Morning Feeding',
              },
            )
          },
        )
      },
    )


    it(
      'requires confirmation before deleting schedule configuration',
      async () => {
        mockedUseFeedingOverview
          .mockReturnValue(
            readyOverview(),
          )

        const confirm =
          vi.spyOn(
            window,
            'confirm',
          ).mockReturnValue(
            true,
          )

        render(
          <FeedingPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Delete',
            },
          ),
        )

        expect(
          confirm,
        ).toHaveBeenCalled()

        await waitFor(
          () => {
            expect(
              deleteSchedule,
            ).toHaveBeenCalledWith(
              schedule.id,
            )
          },
        )

        confirm.mockRestore()
      },
    )


    it(
      'renders calibration history and changes the calibration actuator',
      () => {
        const secondActuator = {
          ...actuator,

          id:
            'actuator-2',

          name:
            'Backup Feeding Actuator',
        }

        mockedUseFeedingOverview
          .mockReturnValue({
            ...readyOverview(),

            actuators: [
              actuator,
              secondActuator,
            ],

            calibrations: [
              calibration,
            ],
          })

        render(
          <FeedingPage />,
        )

        expect(
          screen.getByRole(
            'heading',
            {
              name:
                'Feeder calibration',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'measured_average',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'Unverified',
          ),
        ).toBeInTheDocument()

        fireEvent.change(
          screen.getByLabelText(
            'Calibration actuator',
          ),
          {
            target: {
              value:
                secondActuator.id,
            },
          },
        )

        expect(
          selectCalibrationActuator,
        ).toHaveBeenCalledWith(
          secondActuator.id,
        )
      },
    )


    it(
      'creates a feeder calibration using the real backend fields',
      async () => {
        mockedUseFeedingOverview
          .mockReturnValue(
            readyOverview(),
          )

        render(
          <FeedingPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Add calibration',
            },
          ),
        )

        fireEvent.change(
          screen.getByLabelText(
            'Run count',
          ),
          {
            target: {
              value:
                '5',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Measured seconds',
          ),
          {
            target: {
              value:
                '10',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Measured grams',
          ),
          {
            target: {
              value:
                '50',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Grams per second',
          ),
          {
            target: {
              value:
                '5',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Calibration method',
          ),
          {
            target: {
              value:
                'measured_average',
            },
          },
        )

        const performedAt =
          '2026-09-12T10:30'

        fireEvent.change(
          screen.getByLabelText(
            'Performed at',
          ),
          {
            target: {
              value:
                performedAt,
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Notes',
          ),
          {
            target: {
              value:
                'UI calibration test.',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save calibration',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              createCalibration,
            ).toHaveBeenCalledWith({
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
                new Date(
                  performedAt,
                ).toISOString(),

              verified_by_user_id:
                null,

              notes:
                'UI calibration test.',
            })
          },
        )
      },
    )


    it(
      'updates only changed calibration fields and requests authenticated verification',
      async () => {
        mockedUseFeedingOverview
          .mockReturnValue({
            ...readyOverview(),

            calibrations: [
              calibration,
            ],
          })

        render(
          <FeedingPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Edit calibration',
            },
          ),
        )

        fireEvent.change(
          screen.getByLabelText(
            'Grams per second',
          ),
          {
            target: {
              value:
                '5.25',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'checkbox',
            {
              name:
                'Verified by me',
            },
          ),
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save calibration',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              updateCalibration,
            ).toHaveBeenCalledWith(
              calibration.id,
              {
                grams_per_second:
                  5.25,

                verified_by_user_id:
                  'admin-user',
              },
            )
          },
        )
      },
    )


    it(
      'requires confirmation before deleting a calibration record',
      async () => {
        mockedUseFeedingOverview
          .mockReturnValue({
            ...readyOverview(),

            calibrations: [
              calibration,
            ],
          })

        const confirm =
          vi.spyOn(
            window,
            'confirm',
          ).mockReturnValue(
            true,
          )

        render(
          <FeedingPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Delete calibration',
            },
          ),
        )

        expect(
          confirm,
        ).toHaveBeenCalled()

        await waitFor(
          () => {
            expect(
              deleteCalibration,
            ).toHaveBeenCalledWith(
              calibration.id,
            )
          },
        )

        confirm.mockRestore()
      },
    )


    it(
      'renders fish population history and changes the selected tank',
      () => {
        const secondTank = {
          ...tank,

          id:
            'tank-2',

          name:
            'Second Fish Tank',
        }

        mockedUseFeedingOverview
          .mockReturnValue({
            ...readyOverview(),

            tanks: [
              tank,
              secondTank,
            ],

            populationRecords: [
              populationRecord,
            ],
          })

        render(
          <FeedingPage />,
        )

        expect(
          screen.getByRole(
            'heading',
            {
              name:
                'Fish population',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            '25000',
          ),
        ).toBeInTheDocument()

        fireEvent.change(
          screen.getByLabelText(
            'Population tank',
          ),
          {
            target: {
              value:
                secondTank.id,
            },
          },
        )

        expect(
          selectPopulationTank,
        ).toHaveBeenCalledWith(
          secondTank.id,
        )
      },
    )


    it(
      'creates a fish population record using the canonical backend fields',
      async () => {
        mockedUseFeedingOverview
          .mockReturnValue(
            readyOverview(),
          )

        render(
          <FeedingPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Add population record',
            },
          ),
        )

        fireEvent.change(
          screen.getByLabelText(
            'Count',
          ),
          {
            target: {
              value:
                '100',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Estimated biomass (grams)',
          ),
          {
            target: {
              value:
                '25000',
            },
          },
        )

        const effectiveAt =
          '2026-09-14T08:30'

        fireEvent.change(
          screen.getByLabelText(
            'Effective at',
          ),
          {
            target: {
              value:
                effectiveAt,
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Notes',
          ),
          {
            target: {
              value:
                'Population sampling record.',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save population record',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              createPopulationRecord,
            ).toHaveBeenCalledWith({
              species:
                'Tilapia',

              count:
                100,

              estimated_biomass_grams:
                25000,

              effective_at:
                new Date(
                  effectiveAt,
                ).toISOString(),

              notes:
                'Population sampling record.',
            })
          },
        )
      },
    )


    it(
      'updates only changed fish population fields',
      async () => {
        mockedUseFeedingOverview
          .mockReturnValue({
            ...readyOverview(),

            populationRecords: [
              populationRecord,
            ],
          })

        render(
          <FeedingPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Edit population record',
            },
          ),
        )

        fireEvent.change(
          screen.getByLabelText(
            'Count',
          ),
          {
            target: {
              value:
                '95',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save population record',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              updatePopulationRecord,
            ).toHaveBeenCalledWith(
              populationRecord.id,
              {
                count:
                  95,
              },
            )
          },
        )
      },
    )


    it(
      'requires confirmation before deleting a fish population record',
      async () => {
        mockedUseFeedingOverview
          .mockReturnValue({
            ...readyOverview(),

            populationRecords: [
              populationRecord,
            ],
          })

        const confirm =
          vi.spyOn(
            window,
            'confirm',
          ).mockReturnValue(
            true,
          )

        render(
          <FeedingPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Delete population record',
            },
          ),
        )

        expect(
          confirm,
        ).toHaveBeenCalled()

        await waitFor(
          () => {
            expect(
              deletePopulationRecord,
            ).toHaveBeenCalledWith(
              populationRecord.id,
            )
          },
        )

        confirm.mockRestore()
      },
    )
  },
)