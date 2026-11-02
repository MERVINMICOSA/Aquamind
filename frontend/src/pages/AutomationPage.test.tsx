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
  useAutomationOverview,
} from '../hooks/useAutomationOverview'

import type {
  AutomationRule,
} from '../types/automation'

import {
  AutomationPage,
} from './AutomationPage'


vi.mock(
  '../hooks/useAuth',
  () => ({
    useAuth:
      vi.fn(),
  }),
)


vi.mock(
  '../hooks/useAutomationOverview',
  () => ({
    useAutomationOverview:
      vi.fn(),
  }),
)


vi.mock(
  '../components/automation/AutomationRunHistoryPanel',
  () => ({
    AutomationRunHistoryPanel:
      () => (
        <div
          data-testid="automation-run-history-panel"
        />
      ),
  }),
)


const mockedUseAuth =
  vi.mocked(
    useAuth,
  )


const mockedUseAutomationOverview =
  vi.mocked(
    useAutomationOverview,
  )


const selectSystem =
  vi.fn()

const refresh =
  vi.fn()

const createRule =
  vi.fn(
    async () =>
      true,
  )

const updateRule =
  vi.fn(
    async () =>
      true,
  )

const deleteRule =
  vi.fn(
    async () =>
      true,
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
    '2026-09-19T00:00:00Z',

  updated_at:
    '2026-09-19T00:00:00Z',
}


const sensor = {
  id:
    'sensor-1',

  system_id:
    system.id,

  name:
    'Automation Test Sensor',

  sensor_type:
    'temperature',

  measurement_type:
    'water_temperature',

  location_type:
    'tank',

  location_id:
    null,

  unit:
    'test-unit',

  hardware_identifier:
    null,

  is_simulated:
    true,

  is_enabled:
    true,

  sampling_interval_seconds:
    60,

  calibration_status:
    'unknown',

  created_at:
    '2026-09-19T00:00:00Z',

  updated_at:
    '2026-09-19T00:00:00Z',
}


const actuator = {
  id:
    'actuator-1',

  system_id:
    system.id,

  name:
    'Automation Test Actuator',

  actuator_type:
    'water_pump',

  control_mode:
    'automatic',

  hardware_identifier:
    null,

  location_type:
    null,

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
    '2026-09-19T00:00:00Z',

  updated_at:
    '2026-09-19T00:00:00Z',

  deleted_at:
    null,
}


const rule:
  AutomationRule = {
    id:
      'rule-1',

    system_id:
      system.id,

    name:
      'Temperature Automation',

    description:
      'Synthetic UI automation test rule.',

    trigger_type:
      'sensor_threshold',

    condition_definition: {
      sensor_type:
        sensor.sensor_type,

      measurement_type:
        sensor.measurement_type,

      operator:
        'greater_than',

      value:
        10,
    },

    action_definition: {
      action:
        'activate_actuator',

      actuator_type:
        actuator.actuator_type,

      value:
        1,
    },

    enabled:
      true,

    priority:
      5,

    cooldown_seconds:
      30,

    created_at:
      '2026-09-19T00:00:00Z',

    updated_at:
      '2026-09-19T00:00:00Z',
  }


const legacyRule:
  AutomationRule = {
    ...rule,

    id:
      'rule-2',

    name:
      'Legacy Schedule Rule',

    trigger_type:
      'schedule',

    condition_definition: {
      schedule:
        'synthetic-test-value',
    },

    action_definition: {
      action:
        'activate_actuator',

      actuator_type:
        actuator.actuator_type,

      value:
        1,
    },
  }


function readyOverview():
  ReturnType<
    typeof useAutomationOverview
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

    sensors: [
      sensor,
    ],

    sensorStatus:
      'ready',

    sensorConditionOptions: [
      {
        sensorType:
          sensor.sensor_type,

        measurementType:
          sensor.measurement_type,
      },
    ],

    actuators: [
      actuator,
    ],

    actuatorStatus:
      'ready',

    automationActuatorOptions: [
      {
        actuatorType:
          actuator.actuator_type,

        actuator,
      },
    ],

    rules: [
      rule,
      legacyRule,
    ],

    rulesStatus:
      'ready',

    mutationStatus:
      'idle',

    mutationError:
      null,

    selectSystem,

    createRule,

    updateRule,

    deleteRule,

    refresh,
  }
}


beforeEach(
  () => {
    selectSystem.mockReset()
    refresh.mockReset()

    createRule.mockReset()
    createRule.mockResolvedValue(
      true,
    )

    updateRule.mockReset()
    updateRule.mockResolvedValue(
      true,
    )

    deleteRule.mockReset()
    deleteRule.mockResolvedValue(
      true,
    )

    mockedUseAutomationOverview
      .mockReset()

    mockedUseAutomationOverview
      .mockReturnValue(
        readyOverview(),
      )

    mockedUseAuth
      .mockReset()

    mockedUseAuth
      .mockReturnValue({
        user: {
          role:
            'admin',
        },
      } as ReturnType<typeof useAuth>)
  },
)


describe(
  'AutomationPage',
  () => {
    it(
      'renders persisted rules and changes systems through the overview hook',
      () => {
        mockedUseAutomationOverview
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
          <AutomationPage />,
        )

        expect(
          screen.getByText(
            'Temperature Automation',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'Legacy Schedule Rule',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            /preserved read-only/i,
          ),
        ).toBeInTheDocument()

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
      },
    )


    it(
      'hides rule mutation controls without administrator access',
      () => {
        mockedUseAuth
          .mockReturnValue({
            user:
              null,
          } as ReturnType<typeof useAuth>)

        render(
          <AutomationPage />,
        )

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                'Add automation rule',
            },
          ),
        ).not.toBeInTheDocument()

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                `Edit ${rule.name}`,
            },
          ),
        ).not.toBeInTheDocument()

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                `Delete ${rule.name}`,
            },
          ),
        ).not.toBeInTheDocument()
      },
    )


    it(
      'creates a sensor-threshold rule using the supported backend shape',
      async () => {
        render(
          <AutomationPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Add automation rule',
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
                'New Automation Rule',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Description',
          ),
          {
            target: {
              value:
                'Synthetic rule created by the UI test.',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Threshold value',
          ),
          {
            target: {
              value:
                '12.5',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Requested actuator value',
          ),
          {
            target: {
              value:
                '0.75',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Priority',
          ),
          {
            target: {
              value:
                '7',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Cooldown (seconds)',
          ),
          {
            target: {
              value:
                '45',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save automation rule',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              createRule,
            ).toHaveBeenCalledWith({
              name:
                'New Automation Rule',

              description:
                'Synthetic rule created by the UI test.',

              trigger_type:
                'sensor_threshold',

              condition_definition: {
                sensor_type:
                  sensor.sensor_type,

                measurement_type:
                  sensor.measurement_type,

                operator:
                  'greater_than',

                value:
                  12.5,
              },

              action_definition: {
                action:
                  'activate_actuator',

                actuator_type:
                  actuator.actuator_type,

                value:
                  0.75,
              },

              enabled:
                true,

              priority:
                7,

              cooldown_seconds:
                45,
            })
          },
        )
      },
    )


    it(
      'updates only changed fields for an editable rule',
      async () => {
        render(
          <AutomationPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                `Edit ${rule.name}`,
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
                'Updated Automation Rule',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save automation rule',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              updateRule,
            ).toHaveBeenCalledWith(
              rule.id,
              {
                name:
                  'Updated Automation Rule',
              },
            )
          },
        )
      },
    )


    it(
      'keeps unsupported trigger types read-only',
      () => {
        render(
          <AutomationPage />,
        )

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                `Edit ${legacyRule.name}`,
            },
          ),
        ).not.toBeInTheDocument()

        expect(
          screen.getByRole(
            'button',
            {
              name:
                `Delete ${legacyRule.name}`,
            },
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'requires confirmation before deleting a rule',
      async () => {
        const confirm =
          vi.spyOn(
            window,
            'confirm',
          ).mockReturnValue(
            true,
          )

        render(
          <AutomationPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                `Delete ${rule.name}`,
            },
          ),
        )

        expect(
          confirm,
        ).toHaveBeenCalled()

        await waitFor(
          () => {
            expect(
              deleteRule,
            ).toHaveBeenCalledWith(
              rule.id,
            )
          },
        )

        confirm.mockRestore()
      },
    )


    it(
      'disables creation when no unambiguous automation actuator target exists',
      () => {
        mockedUseAutomationOverview
          .mockReturnValue({
            ...readyOverview(),

            automationActuatorOptions:
              [],
          })

        render(
          <AutomationPage />,
        )

        expect(
          screen.getByRole(
            'button',
            {
              name:
                'Add automation rule',
            },
          ),
        ).toBeDisabled()

        expect(
          screen.getByText(
            /No unambiguous eligible automatic actuator target/i,
          ),
        ).toBeInTheDocument()
      },
    )
  },
)