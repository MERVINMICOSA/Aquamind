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
  useAutomationRunHistory,
} from '../../hooks/useAutomationRunHistory'

import type {
  AutomationRule,
  AutomationRun,
} from '../../types/automation'

import {
  AutomationRunHistoryPanel,
} from './AutomationRunHistoryPanel'


vi.mock(
  '../../hooks/useAutomationRunHistory',
  () => ({
    useAutomationRunHistory:
      vi.fn(),
  }),
)


const mockedUseAutomationRunHistory =
  vi.mocked(
    useAutomationRunHistory,
  )


const selectRule =
  vi.fn()

const nextPage =
  vi.fn()

const previousPage =
  vi.fn()


const rule:
  AutomationRule = {
    id:
      'rule-1',

    system_id:
      'system-1',

    name:
      'Automation Test Rule',

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


const secondRule:
  AutomationRule = {
    ...rule,

    id:
      'rule-2',

    name:
      'Second Automation Rule',
  }


const run:
  AutomationRun = {
    id:
      'run-1',

    rule_id:
      rule.id,

    started_at:
      '2026-09-20T00:00:00Z',

    completed_at:
      null,

    trigger_value:
      0,

    status:
      'synthetic-test-status',

    result_summary:
      null,

    error_message:
      null,
  }


function readyHistory():
  ReturnType<
    typeof useAutomationRunHistory
  > {
  return {
    selectedRuleId:
      rule.id,

    selectedRule:
      rule,

    runs: [
      run,
    ],

    historyStatus:
      'ready',

    hasNext:
      true,

    hasPrevious:
      true,

    pageNumber:
      2,

    selectRule,
    nextPage,
    previousPage,
  }
}


beforeEach(
  () => {
    selectRule.mockReset()
    nextPage.mockReset()
    previousPage.mockReset()

    mockedUseAutomationRunHistory
      .mockReset()

    mockedUseAutomationRunHistory
      .mockReturnValue(
        readyHistory(),
      )
  },
)


describe(
  'AutomationRunHistoryPanel',
  () => {
    it(
      'renders persisted run history and nullable metadata honestly',
      () => {
        render(
          <AutomationRunHistoryPanel
            rules={[
              rule,
            ]}
          />,
        )

        expect(
          screen.getByText(
            'run-1',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            /synthetic-test-status/,
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            /Trigger value:/
          ),
        ).toHaveTextContent(
          'Trigger value: 0',
        )

        expect(
          screen.getAllByText(
            'Not recorded',
            {
              exact:
                false,
            },
          ).length,
        ).toBeGreaterThanOrEqual(
          3,
        )

        expect(
          screen.getByText(
            'Page 2',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'changes the selected automation rule',
      () => {
        render(
          <AutomationRunHistoryPanel
            rules={[
              rule,
              secondRule,
            ]}
          />,
        )

        fireEvent.change(
          screen.getByLabelText(
            'Automation rule',
          ),
          {
            target: {
              value:
                secondRule.id,
            },
          },
        )

        expect(
          selectRule,
        ).toHaveBeenCalledWith(
          secondRule.id,
        )
      },
    )


    it(
      'moves between bounded history pages',
      () => {
        render(
          <AutomationRunHistoryPanel
            rules={[
              rule,
            ]}
          />,
        )

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
      'renders an honest empty history state',
      () => {
        mockedUseAutomationRunHistory
          .mockReturnValue({
            ...readyHistory(),

            runs:
              [],

            hasNext:
              false,

            hasPrevious:
              false,

            pageNumber:
              1,
          })

        render(
          <AutomationRunHistoryPanel
            rules={[
              rule,
            ]}
          />,
        )

        expect(
          screen.getByText(
            'No automation run history recorded for this rule.',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByRole(
            'button',
            {
              name:
                'Previous',
            },
          ),
        ).toBeDisabled()

        expect(
          screen.getByRole(
            'button',
            {
              name:
                'Next',
            },
          ),
        ).toBeDisabled()
      },
    )


    it(
      'renders error and no-rule states',
      () => {
        mockedUseAutomationRunHistory
          .mockReturnValue({
            ...readyHistory(),

            runs:
              [],

            historyStatus:
              'error',

            hasNext:
              false,

            hasPrevious:
              false,
          })

        const {
          rerender,
        } =
          render(
            <AutomationRunHistoryPanel
              rules={[
                rule,
              ]}
            />,
          )

        expect(
          screen.getByRole(
            'alert',
          ),
        ).toHaveTextContent(
          'Unable to load automation run history.',
        )

        rerender(
          <AutomationRunHistoryPanel
            rules={[]}
          />,
        )

        expect(
          screen.getByText(
            'No automation rule is available for run history.',
          ),
        ).toBeInTheDocument()
      },
    )
  },
)