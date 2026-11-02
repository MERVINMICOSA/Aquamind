import {
  act,
  renderHook,
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
  loadAutomationRunHistoryPage,
} from '../services/automationService'

import type {
  AutomationRule,
  AutomationRun,
} from '../types/automation'

import {
  useAutomationRunHistory,
} from './useAutomationRunHistory'


vi.mock(
  '../services/automationService',
  () => ({
    AUTOMATION_RUN_HISTORY_PAGE_SIZE:
      50,

    loadAutomationRunHistoryPage:
      vi.fn(),
  }),
)


const mockedLoadHistory =
  vi.mocked(
    loadAutomationRunHistoryPage,
  )


function rule(
  id: string,
  name: string,
): AutomationRule {
  return {
    id,

    system_id:
      'system-1',

    name,

    description:
      null,

    trigger_type:
      'sensor_threshold',

    condition_definition: {
      sensor_type:
        'synthetic_sensor',

      measurement_type:
        'synthetic_measurement',

      operator:
        'greater_than',

      value:
        1,
    },

    action_definition: {
      action:
        'activate_actuator',

      actuator_type:
        'synthetic_actuator',

      value:
        1,
    },

    enabled:
      true,

    priority:
      0,

    cooldown_seconds:
      0,

    created_at:
      '2026-09-20T00:00:00Z',

    updated_at:
      '2026-09-20T00:00:00Z',
  }
}


function run(
  id: string,
  ruleId: string,
): AutomationRun {
  return {
    id,

    rule_id:
      ruleId,

    started_at:
      '2026-09-20T00:00:00Z',

    completed_at:
      null,

    trigger_value:
      null,

    status:
      'synthetic-test-status',

    result_summary:
      null,

    error_message:
      null,
  }
}


const rules = [
  rule(
    'rule-1',
    'First Rule',
  ),

  rule(
    'rule-2',
    'Second Rule',
  ),
]


beforeEach(
  () => {
    mockedLoadHistory
      .mockReset()
  },
)


describe(
  'useAutomationRunHistory',
  () => {
    it(
      'selects the first current rule and loads its first history page',
      async () => {
        const persistedRun =
          run(
            'run-1',
            'rule-1',
          )

        mockedLoadHistory
          .mockResolvedValue({
            runs: [
              persistedRun,
            ],

            hasNext:
              false,

            hasPrevious:
              false,

            offset:
              0,
          })

        const {
          result,
        } =
          renderHook(
            () =>
              useAutomationRunHistory(
                rules,
              ),
          )

        expect(
          result
            .current
            .selectedRuleId,
        ).toBe(
          'rule-1',
        )

        expect(
          result
            .current
            .historyStatus,
        ).toBe(
          'loading',
        )

        await waitFor(
          () => {
            expect(
              mockedLoadHistory,
            ).toHaveBeenCalledWith(
              'rule-1',
              0,
            )
          },
        )

        await waitFor(
          () => {
            expect(
              result
                .current
                .historyStatus,
            ).toBe(
              'ready',
            )
          },
        )

        expect(
          result
            .current
            .runs,
        ).toEqual([
          persistedRun,
        ])

        expect(
          result
            .current
            .pageNumber,
        ).toBe(
          1,
        )
      },
    )


    it(
      'changes the selected rule and resets pagination',
      async () => {
        mockedLoadHistory
          .mockImplementation(
            async (
              ruleId,
              offset,
            ) => ({
              runs: [
                run(
                  `run-${ruleId}-${offset}`,
                  ruleId,
                ),
              ],

              hasNext:
                false,

              hasPrevious:
                offset >
                0,

              offset,
            }),
          )

        const {
          result,
        } =
          renderHook(
            () =>
              useAutomationRunHistory(
                rules,
              ),
          )

        await waitFor(
          () => {
            expect(
              result
                .current
                .historyStatus,
            ).toBe(
              'ready',
            )
          },
        )

        act(
          () => {
            result
              .current
              .selectRule(
                'rule-2',
              )
          },
        )

        expect(
          result
            .current
            .selectedRuleId,
        ).toBe(
          'rule-2',
        )

        expect(
          result
            .current
            .pageNumber,
        ).toBe(
          1,
        )

        await waitFor(
          () => {
            expect(
              mockedLoadHistory,
            ).toHaveBeenCalledWith(
              'rule-2',
              0,
            )
          },
        )
      },
    )


    it(
      'moves through bounded history pages',
      async () => {
        mockedLoadHistory
          .mockImplementation(
            async (
              ruleId,
              offset,
            ) => ({
              runs: [
                run(
                  `run-${offset}`,
                  ruleId,
                ),
              ],

              hasNext:
                offset ===
                0,

              hasPrevious:
                offset >
                0,

              offset,
            }),
          )

        const {
          result,
        } =
          renderHook(
            () =>
              useAutomationRunHistory(
                rules,
              ),
          )

        await waitFor(
          () => {
            expect(
              result
                .current
                .historyStatus,
            ).toBe(
              'ready',
            )
          },
        )

        expect(
          result
            .current
            .hasNext,
        ).toBe(
          true,
        )

        act(
          () => {
            result
              .current
              .nextPage()
          },
        )

        expect(
          result
            .current
            .pageNumber,
        ).toBe(
          2,
        )

        expect(
          result
            .current
            .hasPrevious,
        ).toBe(
          true,
        )

        await waitFor(
          () => {
            expect(
              mockedLoadHistory,
            ).toHaveBeenCalledWith(
              'rule-1',
              50,
            )
          },
        )

        await waitFor(
          () => {
            expect(
              result
                .current
                .historyStatus,
            ).toBe(
              'ready',
            )
          },
        )

        act(
          () => {
            result
              .current
              .previousPage()
          },
        )

        expect(
          result
            .current
            .pageNumber,
        ).toBe(
          1,
        )

        await waitFor(
          () => {
            expect(
              mockedLoadHistory,
            ).toHaveBeenLastCalledWith(
              'rule-1',
              0,
            )
          },
        )
      },
    )


    it(
      'does not request history when there are no rules',
      () => {
        const {
          result,
        } =
          renderHook(
            () =>
              useAutomationRunHistory(
                [],
              ),
          )

        expect(
          result
            .current
            .selectedRuleId,
        ).toBeNull()

        expect(
          result
            .current
            .selectedRule,
        ).toBeNull()

        expect(
          result
            .current
            .historyStatus,
        ).toBe(
          'ready',
        )

        expect(
          result
            .current
            .runs,
        ).toEqual(
          [],
        )

        expect(
          mockedLoadHistory,
        ).not.toHaveBeenCalled()
      },
    )
  },
)