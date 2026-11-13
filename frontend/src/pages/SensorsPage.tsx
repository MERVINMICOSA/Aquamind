import { useSensorsOverview } from '../hooks/useSensorsOverview'
import { Esp32TelemetryPanel } from '../components/dashboard/Esp32TelemetryPanel'

/**
 * Operator view: current USB sensor measurements, not internal database IDs.
 * Registered sensor details and calibration history remain available by
 * their existing routes for administrator/diagnostic workflows.
 */
export function SensorsPage() {
  const overview = useSensorsOverview()

  return (
    <section className="section-page">
      <header className="sensors-page-heading">
        <div>
          <p className="eyebrow">Monitoring</p>
          <h1>Sensors</h1>
          <p className="page-description">
            Only sensors with current, usable ESP32 readings are shown as active.
            Measurements update automatically when new packets arrive.
          </p>
        </div>

        {overview.systems.length > 0 && (
          <div className="system-selector">
            <label htmlFor="sensors-system">Aquaponics system</label>
            <select
              id="sensors-system"
              value={overview.selectedSystemId ?? ''}
              onChange={(event) => overview.selectSystem(event.target.value)}
            >
              {overview.systems.map((system) => (
                <option key={system.id} value={system.id}>{system.name}</option>
              ))}
            </select>
          </div>
        )}
      </header>

      {overview.systemsStatus === 'loading' && (
        <p role="status">Loading aquaponics systems...</p>
      )}
      {overview.systemsStatus === 'error' && (
        <div className="status-message status-message--error" role="alert">
          {overview.errorMessage ?? 'Unable to load aquaponics systems.'}
        </div>
      )}
      {overview.systemsStatus === 'ready' && overview.systems.length === 0 && (
        <div className="empty-state">
          <h2>No aquaponics system configured</h2>
          <p>Create an AquaMind system before monitoring sensors.</p>
        </div>
      )}
      {overview.selectedSystem !== null && (
        <Esp32TelemetryPanel
          key={overview.selectedSystem.id}
          systemId={overview.selectedSystem.id}
          mode="simple"
        />
      )}
    </section>
  )
}
