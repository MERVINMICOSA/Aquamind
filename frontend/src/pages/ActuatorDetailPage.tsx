import { Link, useParams } from 'react-router-dom'
import { useActuatorDetail } from '../hooks/useActuatorDetail'

function formatValue(value: string | null): string {
  return value === null ? 'Not recorded' : value.replaceAll('_', ' ')
}

function formatTimestamp(value: string | null): string {
  if (value === null) return 'Not recorded'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export function ActuatorDetailPage() {
  const { actuatorId } = useParams<{ actuatorId: string }>()
  const detail = useActuatorDetail(actuatorId)
  const actuator = detail.actuator

  return (
    <section className="section-page">
      <header className="sensor-detail-heading">
        <div>
          <Link to="/actuators" className="sensor-detail-back-link">← Actuators</Link>
          <p className="eyebrow">Actuator Detail</p>
          <h1>{actuator?.name ?? 'Actuator'}</h1>
          <p className="page-description">Inspect actuator configuration and persisted software event history.</p>
        </div>
      </header>
      {actuatorId === undefined ? (
        <div role="alert">Actuator identifier is missing.</div>
      ) : detail.actuatorStatus === 'loading' ? (
        <div role="status" className="status-message">
          Loading actuator...
        </div>
      ) : detail.actuatorStatus === 'error' ? (
        <div
          role="alert"
          className="status-message status-message--error"
        >
          Unable to load this actuator.
        </div>
      ) : actuator !== null && (
        <>
          <section className="sensor-detail-panel">
            <h2>Actuator configuration</h2>
            <dl className="sensor-detail-configuration">
              <div><dt>Actuator type</dt><dd>{formatValue(actuator.actuator_type)}</dd></div>
              <div><dt>Control mode</dt><dd>{formatValue(actuator.control_mode)}</dd></div>
              <div><dt>Enabled</dt><dd>{actuator.is_enabled ? 'Yes' : 'No'}</dd></div>
              <div><dt>Location type</dt><dd>{formatValue(actuator.location_type)}</dd></div>
              <div><dt>Location ID</dt><dd>{actuator.location_id ?? 'Not recorded'}</dd></div>
              <div><dt>Hardware identifier</dt><dd>{actuator.hardware_identifier ?? 'Not recorded'}</dd></div>
              <div><dt>Safety configuration</dt><dd>{actuator.safety_config === null
                ? 'Not recorded' : JSON.stringify(actuator.safety_config)}</dd></div>
            </dl>
          </section>
          <section className="sensor-detail-panel">
            <h2>Persisted state</h2>
            {actuator.last_state_at === null ? (
              <p>No state recorded</p>
            ) : (
              <dl className="sensor-detail-configuration">
                <div><dt>State</dt><dd>{formatValue(actuator.current_state)}</dd></div>
                <div><dt>Value</dt><dd>{actuator.current_value ?? 'Not recorded'}</dd></div>
                <div><dt>State recorded</dt><dd>{formatTimestamp(actuator.last_state_at)}</dd></div>
              </dl>
            )}
            <p className="actuator-hardware-note">Persisted state and software events do not confirm physical actuator execution or connection.</p>
          </section>
          <section className="sensor-detail-panel" aria-labelledby="actuator-history-heading">
            <div className="sensor-detail-history-heading">
              <h2 id="actuator-history-heading">Persisted software event history</h2>
              <span className="sensor-detail-history-page">Page {detail.pageNumber}</span>
            </div>
            {detail.historyStatus === 'loading' && <div role="status">Loading event history...</div>}
            {detail.historyStatus === 'error' && <div role="alert">Unable to load actuator event history.</div>}
            {detail.historyStatus === 'ready' && (detail.events.length === 0 ? (
              <p>No persisted software events on this page.</p>
            ) : (
              <div className="sensor-history-table-wrap">
                <table className="sensor-history-table" aria-label="Persisted software event history">
                  <thead><tr>
                    {['Started', 'Command', 'Trigger source', 'Recorded status', 'Requested value', 'Actual value',
                      'Completed', 'Duration (ms)', 'Fault code', 'Error message', 'Created'].map(label => <th key={label}>{label}</th>)}
                  </tr></thead>
                  <tbody>{detail.events.map(event => (
                    <tr key={event.id}>
                      <td>{formatTimestamp(event.started_at)}</td>
                      <td>{formatValue(event.command_type)}</td>
                      <td>{formatValue(event.trigger_source)}</td>
                      <td>{formatValue(event.status)}</td>
                      <td>{event.requested_value ?? 'Not recorded'}</td>
                      <td>{event.actual_value ?? 'Not recorded'}</td>
                      <td>{formatTimestamp(event.completed_at)}</td>
                      <td>{event.duration_ms ?? 'Not recorded'}</td>
                      <td>{event.fault_code ?? 'Not recorded'}</td>
                      <td>{event.error_message ?? 'Not recorded'}</td>
                      <td>{formatTimestamp(event.created_at)}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            ))}
            <footer className="sensor-history-pagination">
              <span>Up to 50 events per page</span>
              <div>
                <button type="button" className="sensor-history-button" onClick={detail.previousPage}
                  disabled={!detail.hasPrevious || detail.historyStatus === 'loading'}>Previous</button>
                <button type="button" className="sensor-history-button" onClick={detail.nextPage}
                  disabled={!detail.hasNext || detail.historyStatus !== 'ready'}>Next</button>
              </div>
            </footer>
          </section>
        </>
      )}
    </section>
  )
}
