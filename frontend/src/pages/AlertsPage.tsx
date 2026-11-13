import { useState } from 'react'
import {
  useAlertsOverview,
} from '../hooks/useAlertsOverview'


function formatTimestamp(
  value: string | null,
): string {
  if (value === null) {
    return 'Not recorded'
  }

  const date =
    new Date(value)

  return Number.isNaN(
    date.getTime(),
  )
    ? value
    : date.toLocaleString()
}


export function AlertsPage() {
  const overview =
    useAlertsOverview()
  const [resolutionDraft, setResolutionDraft] = useState<{
    alertId: string
    reason: string
    error: string | null
  } | null>(null)

  const activeOnPage = overview.alerts.filter(
    (alert) => alert.status === 'active',
  ).length
  const acknowledgedOnPage = overview.alerts.filter(
    (alert) => alert.status === 'acknowledged',
  ).length

  return (
    <section className="section-page alerts-page">
      <header className="page-heading-row">
        <div>
          <p className="eyebrow">
            System Awareness
          </p>

          <h1>
            Alerts
          </h1>

          <p className="page-description">
            Review water-quality warnings, sensor faults, and saved alert
            history for the selected system. Acknowledging or resolving an
            alert records your review; it does not operate the water pump.
          </p>
        </div>

        {
          overview.systems.length >
            0 && (
            <div className="select-field">
              <label htmlFor="alerts-system">
                Aquaponics system
              </label>

              <select
                id="alerts-system"
                value={
                  overview.selectedSystemId ??
                  ''
                }
                onChange={
                  (event) =>
                    {
                    setResolutionDraft(null)
                    overview.selectSystem(event.target.value)
                  }
                }
              >
                {
                  overview.systems.map(
                    (system) => (
                      <option
                        key={system.id}
                        value={system.id}
                      >
                        {system.name}
                      </option>
                    ),
                  )
                }
              </select>
            </div>
          )
        }
      </header>

      <section className="surface-panel" aria-labelledby="alerts-guide-heading">
        <div>
          <p className="eyebrow">Page guide</p>
          <h2 id="alerts-guide-heading">How to use Alerts</h2>
          <p>
            Review the alert severity, cause, associated sensor, and recorded
            value. Check the Sensors page and the physical aquaponics system
            before taking corrective action. Acknowledge when reviewed;
            resolve only after the condition has been addressed and record
            what was done.
          </p>
          <h3>What does this page need?</h3>
          <ul>
            <li>A configured AquaMind system with persisted sensor readings.</li>
            <li>Appropriate enabled alert thresholds and verified readings
              where calibration matters, especially pH and TDS.</li>
            <li>An operator who can inspect equipment and confirm the
              actual condition before resolving an alert.</li>
          </ul>
          <p>
            Raw ESP32 USB packets alone do not create threshold alerts.
            The external circulation pump cannot be started or stopped here.
            Notifications outside the website are not implied.
          </p>
        </div>
      </section>

      {
        overview.systemsStatus ===
          'loading' && (
          <div
            role="status"
            className="status-message"
          >
            Loading AquaMind systems...
          </div>
        )
      }

      {
        overview.systemsStatus ===
          'error' && (
          <div
            role="alert"
            className="status-message status-message--error"
          >
            Unable to load AquaMind systems.
          </div>
        )
      }

      {
        overview.systemsStatus ===
          'ready' &&
        overview.systems.length ===
          0 && (
          <div className="empty-state">
            <h2>
              No aquaponics system configured
            </h2>

            <p>
              No system is available for viewing alert history.
            </p>
          </div>
        )
      }

      {
        overview.selectedSystem !==
          null && (
          <section
            className="surface-panel"
            aria-labelledby="alerts-history-heading"
          >
            <div className="panel-heading-row">
              <div>
                <h2 id="alerts-history-heading">
                  Persisted alert history
                </h2>

                <p>
                  {
                    overview
                      .selectedSystem
                      .name
                  }
                </p>
              </div>

              <span className="page-indicator">
                Page {overview.pageNumber}
              </span>
            </div>

            <p className="data-note">
              Alert history is persisted application data, not hardware evidence.
            </p>

            {overview.historyStatus === 'ready' && (
              <p className="page-description">
                On this page: {activeOnPage} active, {acknowledgedOnPage} acknowledged,
                {' '}{overview.alerts.length - activeOnPage - acknowledgedOnPage} resolved.
                Counts describe only the currently loaded history page, not every
                alert in the system.
              </p>
            )}

            {overview.mutationError !== null && (
              <div className="status-message status-message--error" role="alert">
                {overview.mutationError}
              </div>
            )}

            {
              overview.historyStatus ===
                'loading' && (
                <div role="status">
                  Loading alert history...
                </div>
              )
            }

            {
              overview.historyStatus ===
                'error' && (
                <div
                  role="alert"
                  className="status-message status-message--error"
                >
                  Unable to load alert history for the selected system.
                </div>
              )
            }

            {
              overview.historyStatus ===
                'ready' &&
              (
                overview.alerts.length ===
                  0
                  ? (
                    <p>
                      No persisted alerts on this page.
                    </p>
                  )
                  : (
                    <div className="data-table-wrap">
                      <table
                        className="data-table"
                        aria-label="Persisted alert history"
                      >
                        <thead>
                          <tr>
                            {
                              [
                                'Severity',
                                'Status',
                                'Alert type',
                                'Message',
                                'Created',
                                'Associated resources',
                                'Trigger value',
                                'Acknowledgment',
                                'Resolution',
                                'Review actions',
                              ].map(
                                (label) => (
                                  <th key={label}>
                                    {label}
                                  </th>
                                ),
                              )
                            }
                          </tr>
                        </thead>

                        <tbody>
                          {
                            overview.alerts.map(
                              (alert) => (
                                <tr key={alert.id}>
                                  <td>
                                    {alert.severity}
                                  </td>

                                  <td>
                                    {alert.status}
                                  </td>

                                  <td>
                                    {alert.alert_type}
                                  </td>

                                  <td>
                                    {alert.message}
                                  </td>

                                  <td>
                                    {formatTimestamp(
                                      alert.created_at,
                                    )}
                                  </td>

                                  <td>
                                    <dl>
                                      <dt>
                                        Sensor ID
                                      </dt>
                                      <dd>
                                        {
                                          alert.sensor_id ??
                                          'Not recorded'
                                        }
                                      </dd>

                                      <dt>
                                        Actuator ID
                                      </dt>
                                      <dd>
                                        {
                                          alert.actuator_id ??
                                          'Not recorded'
                                        }
                                      </dd>

                                      <dt>
                                        Threshold ID
                                      </dt>
                                      <dd>
                                        {
                                          alert.threshold_id ??
                                          'Not recorded'
                                        }
                                      </dd>
                                    </dl>
                                  </td>

                                  <td>
                                    {
                                      alert.trigger_value ??
                                      'Not recorded'
                                    }
                                  </td>

                                  <td>
                                    <dl>
                                      <dt>
                                        Acknowledged at
                                      </dt>
                                      <dd>
                                        {formatTimestamp(
                                          alert.acknowledged_at,
                                        )}
                                      </dd>

                                      <dt>
                                        User ID
                                      </dt>
                                      <dd>
                                        {
                                          alert.acknowledged_by_user_id ??
                                          'Not recorded'
                                        }
                                      </dd>
                                    </dl>
                                  </td>

                                  <td>
                                    <dl>
                                      <dt>
                                        Resolved at
                                      </dt>
                                      <dd>
                                        {formatTimestamp(
                                          alert.resolved_at,
                                        )}
                                      </dd>

                                      <dt>
                                        Reason
                                      </dt>
                                      <dd>
                                        {
                                          alert.resolution_reason ??
                                          'Not recorded'
                                        }
                                      </dd>
                                    </dl>
                                  </td>

                                  <td>
                                    {alert.status === 'active' && (
                                      <button
                                        type="button"
                                        className="secondary-button"
                                        disabled={overview.mutationStatus === 'saving'}
                                        onClick={() => {
                                          void overview.acknowledgeAlert(alert)
                                        }}
                                      >
                                        Acknowledge
                                      </button>
                                    )}

                                    {alert.status === 'acknowledged' && (
                                      <>
                                        <button
                                          type="button"
                                          className="secondary-button"
                                          disabled={overview.mutationStatus === 'saving'}
                                          onClick={() => setResolutionDraft({
                                            alertId: alert.id,
                                            reason: '',
                                            error: null,
                                          })}
                                        >
                                          Resolve
                                        </button>

                                        {resolutionDraft?.alertId === alert.id && (
                                          <form
                                            onSubmit={(event) => {
                                              event.preventDefault()
                                              const reason = resolutionDraft.reason.trim()
                                              if (!reason) {
                                                setResolutionDraft({
                                                  ...resolutionDraft,
                                                  error: 'Describe the corrective action first.',
                                                })
                                                return
                                              }
                                              void overview.resolveAlert(alert, reason)
                                                .then((saved) => {
                                                  if (saved) setResolutionDraft(null)
                                                })
                                            }}
                                          >
                                            <label htmlFor={`alert-resolution-${alert.id}`}>
                                              Resolution reason
                                            </label>
                                            <input
                                              id={`alert-resolution-${alert.id}`}
                                              type="text"
                                              maxLength={500}
                                              required
                                              value={resolutionDraft.reason}
                                              disabled={overview.mutationStatus === 'saving'}
                                              onChange={(event) => setResolutionDraft({
                                                ...resolutionDraft,
                                                reason: event.target.value,
                                                error: null,
                                              })}
                                            />
                                            {resolutionDraft.error && (
                                              <p role="alert">{resolutionDraft.error}</p>
                                            )}
                                            <button
                                              type="submit"
                                              className="secondary-button"
                                              disabled={overview.mutationStatus === 'saving'}
                                            >
                                              Confirm resolution
                                            </button>
                                            <button
                                              type="button"
                                              className="secondary-button"
                                              onClick={() => setResolutionDraft(null)}
                                            >
                                              Cancel
                                            </button>
                                          </form>
                                        )}
                                      </>
                                    )}

                                    {alert.status === 'resolved' && (
                                      <span>Resolved</span>
                                    )}
                                  </td>
                                </tr>
                              ),
                            )
                          }
                        </tbody>
                      </table>
                    </div>
                  )
              )
            }

            <footer className="data-pagination">
              <span>
                Up to 50 alerts per page
              </span>

              <div className="data-pagination__actions">
                <button
                  type="button"
                  className="secondary-button"
                  disabled={
                    !overview.hasPrevious ||
                    overview.historyStatus ===
                      'loading'
                  }
                  onClick={
                    overview.previousPage
                  }
                >
                  Previous
                </button>

                <button
                  type="button"
                  className="secondary-button"
                  disabled={
                    !overview.hasNext ||
                    overview.historyStatus !==
                      'ready'
                  }
                  onClick={
                    overview.nextPage
                  }
                >
                  Next
                </button>
              </div>
            </footer>
          </section>
        )
      }
    </section>
  )
}