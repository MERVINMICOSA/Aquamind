import {
  useAutomationRunHistory,
} from '../../hooks/useAutomationRunHistory'

import type {
  AutomationRule,
} from '../../types/automation'


interface AutomationRunHistoryPanelProps {
  rules: AutomationRule[]
}


function displayNullable(
  value: string | null,
): string {
  return value ??
    'Not recorded'
}


export function AutomationRunHistoryPanel({
  rules,
}: AutomationRunHistoryPanelProps) {
  const history =
    useAutomationRunHistory(
      rules,
    )


  return (
    <section
      className="sensor-detail-panel"
    >
      <div>
        <p
          className="eyebrow"
        >
          Activity
        </p>

        <h2>
          Automation activity
        </h2>

        <p
          className="page-description"
        >
          Persisted automation run history for the selected
          rule. This records application runtime activity and
          does not establish physical hardware execution.
        </p>
      </div>


      {
        rules.length ===
          0 ? (
          <div
            className="empty-state"
          >
            No automation rule is available for run history.
          </div>
        ) : (
          <>
            <label
              className="system-selector"
            >
              <span>
                Automation rule
              </span>

              <select
                value={
                  history.selectedRuleId ??
                  ''
                }
                onChange={
                  (event) =>
                    history.selectRule(
                      event.target.value,
                    )
                }
              >
                {
                  rules.map(
                    (rule) => (
                      <option
                        key={
                          rule.id
                        }
                        value={
                          rule.id
                        }
                      >
                        {rule.name}
                      </option>
                    ),
                  )
                }
              </select>
            </label>


            {
              history.historyStatus ===
                'loading' && (
                <p
                  className="status-message"
                >
                  Loading automation run history…
                </p>
              )
            }


            {
              history.historyStatus ===
                'error' && (
                <p
                  className="status-message status-message--error"
                  role="alert"
                >
                  Unable to load automation run history.
                </p>
              )
            }


            {
              history.historyStatus ===
                'ready' &&
              history.runs.length ===
                0 && (
                <div
                  className="empty-state"
                >
                  No automation run history recorded for this
                  rule.
                </div>
              )
            }


            {
              history.historyStatus ===
                'ready' &&
              history.runs.map(
                (run) => (
                  <article
                    key={
                      run.id
                    }
                    className="sensor-detail-panel"
                  >
                    <h3>
                      {run.id}
                    </h3>

                    <p>
                      Status:{' '}
                      {
                        run.status
                      }
                    </p>

                    <p>
                      Started:{' '}
                      {
                        run.started_at
                      }
                    </p>

                    <p>
                      Completed:{' '}
                      {
                        displayNullable(
                          run.completed_at,
                        )
                      }
                    </p>

                    <p>
                      Trigger value:{' '}
                      {
                        run.trigger_value ??
                        'Not recorded'
                      }
                    </p>

                    <p>
                      Result summary:{' '}
                      {
                        displayNullable(
                          run.result_summary,
                        )
                      }
                    </p>

                    <p>
                      Error message:{' '}
                      {
                        displayNullable(
                          run.error_message,
                        )
                      }
                    </p>
                  </article>
                ),
              )
            }


            <div>
              <button
                type="button"
                disabled={
                  history.historyStatus ===
                    'loading' ||
                  !history.hasPrevious
                }
                onClick={
                  history.previousPage
                }
              >
                Previous
              </button>

              <span>
                Page{' '}
                {
                  history.pageNumber
                }
              </span>

              <button
                type="button"
                disabled={
                  history.historyStatus !==
                    'ready' ||
                  !history.hasNext
                }
                onClick={
                  history.nextPage
                }
              >
                Next
              </button>
            </div>
          </>
        )
      }
    </section>
  )
}