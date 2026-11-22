import type { Esp32Telemetry } from '../../types/esp32Telemetry'
import { evaluateEsp32Warnings, isFreshEsp32Packet } from './esp32WarningRules'
import './Esp32TelemetryWarnings.css'

interface Props {
  latest: Esp32Telemetry | null
  nowMs: number
  demo?: boolean
}

/** Informational website warnings; they never trigger hardware or backend alerts. */
export function Esp32TelemetryWarnings({ latest, nowMs, demo = false }: Props) {
  if (demo || latest === null || !isFreshEsp32Packet(latest.received_at, nowMs)) {
    return null
  }

  const warnings = evaluateEsp32Warnings(latest.packet)
  const hasUsableSensor = [
    latest.packet.water_level_pct,
    latest.packet.water_temp_c,
    latest.packet.air_temp_c,
    latest.packet.humidity_pct,
    latest.packet.ph_calibrated ? latest.packet.ph : null,
    latest.packet.tds_calibrated ? latest.packet.tds_ppm : null,
  ].some(value => value !== null && value !== undefined && Number.isFinite(value))

  if (warnings.length === 0 && !hasUsableSensor) return null

  return (
    <section
      className="esp32-warning-panel"
      data-state={warnings.length > 0 ? 'attention' : 'normal'}
      aria-label="ESP32 monitoring warnings"
    >
      <div className="esp32-warning-panel__header">
        <span className="esp32-warning-panel__icon" aria-hidden="true">
          {warnings.length > 0 ? '!' : '✓'}
        </span>
        <div>
          <h3>{warnings.length > 0
            ? `${warnings.length} sensor ${warnings.length === 1 ? 'warning' : 'warnings'}`
            : 'No active threshold warnings'}
          </h3>
          <p>
            {warnings.length > 0
              ? 'Based on the most recent ESP32 packet. Investigate before making adjustments.'
              : 'Available fresh readings have no triggered advisory thresholds.'}
          </p>
        </div>
      </div>
      {warnings.length > 0 && (
        <ul className="esp32-warning-panel__items">
          {warnings.map(warning => (
            <li key={warning.id}>
              <strong>{warning.title}</strong>
              <span>{warning.message}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="esp32-warning-panel__footnote">
        Thresholds are advisory only. Missing readings are not assumed safe;
        ESP32-reported pH and TDS calibration is not independently verified.
      </p>
    </section>
  )
}
