import { Link } from 'react-router-dom'

/**
 * The circulation pump is powered and managed outside AquaMind.
 * This page contains no actuator commands, implied pump status, or
 * automatic control features.
 */
export function WaterFlowPage() {
  return (
    <section className="section-page">
      <header className="page-heading">
        <p className="eyebrow">Aquaponics plumbing</p>
        <h1>Water flow</h1>
        <p className="page-description">
          Reference the continuously circulating fish-tank and two-raft layout.
          Circulation is powered externally; the ESP32 and Raspberry Pi monitor
          the system and do not switch pumps or relays.
        </p>
      </header>

      <section className="surface-panel" aria-labelledby="water-flow-path">
        <div>
          <p className="eyebrow">Planned flow path</p>
          <h2 id="water-flow-path">Continuous water circulation</h2>
          <ol>
            <li><strong>Tilapia fish tank</strong> — starting and returning water source.</li>
            <li><strong>External circulation pump</strong> — moves tank water to the upper grow raft without an ESP32 relay.</li>
            <li><strong>Upper lettuce raft</strong> — receives water from the pump.</li>
            <li><strong>Gravity-fed PVC transfer</strong> — carries overflow to the lower grow raft.</li>
            <li><strong>Lower lettuce raft</strong> — receives water from the upper raft.</li>
            <li><strong>Gravity return</strong> — brings water back to the fish tank to complete the loop.</li>
          </ol>
          <p>
            Install appropriate solids and biological filtration as required.
            The exact filter placement, pipe sizing, overflow capacity, and
            return height must be checked against the physical installation.
          </p>
        </div>
      </section>

      <section className="surface-panel" aria-labelledby="water-flow-monitoring">
        <div>
          <p className="eyebrow">Sensor-only operation</p>
          <h2 id="water-flow-monitoring">What AquaMind measures</h2>
          <p>
            Review temperature, pH, TDS, air conditions, and water-level
            readings on the Sensors page. Only verified calibrated measurements
            should be used for water-quality decisions.
          </p>
          <p>
            Monitoring the water level is not the same as verifying water flow.
            Without a dedicated flow sensor or other independent confirmation,
            AquaMind cannot determine that an external circulation pump is running.
          </p>
          <Link to="/sensors" className="sensor-detail-link">
            Review sensor readings
          </Link>
        </div>
      </section>

      <section className="surface-panel" aria-labelledby="water-flow-safety">
        <div>
          <p className="eyebrow">Physical safety</p>
          <h2 id="water-flow-safety">What the installation needs</h2>
          <ul>
            <li>Suitable continuous-duty pump and safe, protected electrical supply.</li>
            <li>Proper gravity drain and emergency overflow capacity to prevent flooding.</li>
            <li>Protection against blocked pipes, dry running, and power failure.</li>
            <li>Safe plumbing supports, accessible isolation and maintenance points.</li>
          </ul>
          <p>
            AquaMind does not provide a stop, start, refill, or pump override
            for this external loop. Verify protection physically, not through
            a software control or inferred pump state.
          </p>
        </div>
      </section>
    </section>
  )
}
