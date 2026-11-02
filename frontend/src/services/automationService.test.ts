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
  AUTOMATION_RUN_HISTORY_PAGE_SIZE,
  createAutomationRule,
  deleteAutomationRule,
  listAutomationRules,
  loadAutomationRunHistoryPage,
  updateAutomationRule,
} from './automationService'

import type {
  AutomationRun,
  SensorThresholdAutomationRuleInput,
} from '../types/automation'


vi.mock(
  './apiClient',
  () => ({
    apiRequest:
      vi.fn(),
  }),
)


const mockedApiRequest =
  vi.mocked(
    apiRequest,
  )


const input:
  SensorThresholdAutomationRuleInput = {
    name:
      'Automation Test Rule',

    description:
      'Synthetic service serialization fixture.',

    trigger_type:
      'sensor_threshold',

    condition_definition: {
      sensor_type:
        'temperature',

      measurement_type:
        'water_temperature',

      operator:
        'greater_than',

      value:
        10,
    },

    action_definition: {
      action:
        'activate_actuator',

      actuator_type:
        'water_pump',

      value:
        1,
    },

    enabled:
      true,

    priority:
      10,

    cooldown_seconds:
      60,
  }


function automationRun(
  index: number,
): AutomationRun {
  return {
    id:
      `run-${index}`,

    rule_id:
      'rule-1',

    started_at:
      `2026-09-20T00:${String(
        index % 60,
      ).padStart(2, '0')}:00Z`,

    completed_at:
      null,

    trigger_value:
      index,

    status:
      'synthetic-test-status',

    result_summary:
      null,

    error_message:
      null,
  }
}


beforeEach(
  () => {
    mockedApiRequest
      .mockReset()
  },
)


describe(
  'automationService',
  () => {
    it(
      'lists rules for one encoded system',
      async () => {
        mockedApiRequest
          .mockResolvedValue(
            [],
          )

        const result =
          await listAutomationRules(
            'system / one',
          )

        expect(
          result,
        ).toEqual(
          [],
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'automation-rules?system_id=system%20%2F%20one',
        )
      },
    )


    it(
      'creates a sensor-threshold rule for the system',
      async () => {
        mockedApiRequest
          .mockResolvedValue(
            {
              id:
                'rule-1',
            },
          )

        await createAutomationRule(
          'system-1',
          input,
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'automation-rules',
          {
            method:
              'POST',

            body:
              JSON.stringify({
                system_id:
                  'system-1',

                ...input,
              }),
          },
        )
      },
    )


    it(
      'updates an encoded rule id',
      async () => {
        mockedApiRequest
          .mockResolvedValue(
            {
              id:
                'rule-1',
            },
          )

        await updateAutomationRule(
          'rule / one',
          {
            enabled:
              false,

            priority:
              5,
          },
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'automation-rules/rule%20%2F%20one',
          {
            method:
              'PATCH',

            body:
              JSON.stringify({
                enabled:
                  false,

                priority:
                  5,
              }),
          },
        )
      },
    )


    it(
      'deletes an encoded rule id',
      async () => {
        mockedApiRequest
          .mockResolvedValue(
            undefined,
          )

        await deleteAutomationRule(
          'rule / one',
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'automation-rules/rule%20%2F%20one',
          {
            method:
              'DELETE',
          },
        )
      },
    )


    it(
      'loads bounded automation run history with one lookahead record',
      async () => {
        const response =
          Array.from(
            {
              length:
                AUTOMATION_RUN_HISTORY_PAGE_SIZE +
                1,
            },
            (
              _,
              index,
            ) =>
              automationRun(
                index,
              ),
          )

        mockedApiRequest
          .mockResolvedValue(
            response,
          )

        const page =
          await loadAutomationRunHistoryPage(
            'rule / one',
            50,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'automation-runs/history?rule_id=rule%20%2F%20one' +
            '&limit=51&offset=50',
        )

        expect(
          page.runs,
        ).toHaveLength(
          50,
        )

        expect(
          page.runs,
        ).toEqual(
          response.slice(
            0,
            50,
          ),
        )

        expect(
          page.hasNext,
        ).toBe(
          true,
        )

        expect(
          page.hasPrevious,
        ).toBe(
          true,
        )

        expect(
          page.offset,
        ).toBe(
          50,
        )
      },
    )


    it(
      'reports no next page when the response fits within one page',
      async () => {
        const response = [
          automationRun(
            1,
          ),

          automationRun(
            2,
          ),
        ]

        mockedApiRequest
          .mockResolvedValue(
            response,
          )

        const page =
          await loadAutomationRunHistoryPage(
            'rule-1',
            0,
          )

        expect(
          page.runs,
        ).toEqual(
          response,
        )

        expect(
          page.hasNext,
        ).toBe(
          false,
        )

        expect(
          page.hasPrevious,
        ).toBe(
          false,
        )

        expect(
          page.offset,
        ).toBe(
          0,
        )
      },
    )


    it(
      'normalizes negative and fractional history offsets',
      async () => {
        mockedApiRequest
          .mockResolvedValue(
            [],
          )

        const page =
          await loadAutomationRunHistoryPage(
            'rule-1',
            -12.8,
          )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'automation-runs/history?rule_id=rule-1' +
            '&limit=51&offset=0',
        )

        expect(
          page.offset,
        ).toBe(
          0,
        )

        expect(
          page.hasPrevious,
        ).toBe(
          false,
        )
      },
    )
  },
)