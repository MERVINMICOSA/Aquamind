import { useEffect, useState } from 'react'
import { listEsp32Telemetry } from '../../services/esp32TelemetryService'
import { loadSystemSensorOverview } from '../../services/sensorService'
import type { SystemSensorOverview } from '../../services/sensorService'
import type { DashboardSensor } from '../../types/dashboard'
import type { Esp32RawReadings, Esp32RawSensorReading, Esp32SensorPacket, Esp32Telemetry } from '../../types/esp32Telemetry'
import './Esp32TelemetryPanel.css'

interface Props {
  systemId: string
  /** Offline-only fixture, supplied by the demo dashboard. Never fetched. */
  demoPackets?: Esp32Telemetry[]
  /** Simplified monitoring view: only current readings, no internal IDs. */
  mode?: 'details' | 'simple'
}

function numeric(value: number | null, suffix = '', digits = 2): string {
  return value === null ? 'No reading' : `${value.toFixed(digits)}${suffix}`
}

function timestamp(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleString()
}

type SignalHealth = {
  state: 'connected' | 'stale' | 'disconnected' | 'unknown'
  label: string
  detail: string
}

function signalHealth(
  latest: Esp32Telemetry | null,
  requestStatus: 'loading' | 'ready' | 'error',
  nowMs: number,
): SignalHealth {
  if (requestStatus === 'error') {
    return { state: 'unknown', label: 'Status unavailable', detail: 'Cannot refresh telemetry from the backend.' }
  }
  if (requestStatus === 'loading') {
    return { state: 'unknown', label: 'Checking connection', detail: 'Loading saved ESP32 packets.' }
  }
  if (latest === null) {
    return { state: 'stale', label: 'No recent data', detail: 'No ESP32 packets have been saved for this system yet.' }
  }

  const receivedMs = Date.parse(latest.received_at)
  if (!Number.isFinite(receivedMs) || receivedMs - nowMs > 10_000) {
    return { state: 'unknown', label: 'Status unavailable', detail: 'Packet timestamp is invalid or clocks differ.' }
  }

  const ageSeconds = Math.max(0, Math.floor((nowMs - receivedMs) / 1000))
  if (ageSeconds < 15) {
    return { state: 'connected', label: 'Connected', detail: `Latest packet received ${ageSeconds}s ago.` }
  }
  if (ageSeconds < 45) {
    return { state: 'stale', label: 'No recent data', detail: `Latest packet received ${ageSeconds}s ago. The ESP32 may be reconnecting.` }
  }
  return {
    state: 'disconnected',
    label: 'Disconnected',
    detail: `No packet for ${ageSeconds}s. Inferred from missing data; USB may still be plugged in.`,
  }
}

function fields(packet: Esp32SensorPacket) {
  return [
    { label: 'Water temperature', value: numeric(packet.water_temp_c, ' °C') },
    { label: 'pH', value: packet.ph_calibrated ? numeric(packet.ph) : 'Not calibrated' },
    { label: 'TDS', value: packet.tds_calibrated ? numeric(packet.tds_ppm, ' ppm', 0) : 'Not calibrated' },
    { label: 'Water level', value: numeric(packet.water_level_pct, '%') },
    { label: 'Air temperature', value: numeric(packet.air_temp_c, ' °C') },
    { label: 'Air humidity', value: numeric(packet.humidity_pct, '%') },
    { label: 'Ultrasonic distance', value: numeric(packet.distance_cm, ' cm') },
    { label: 'Water height', value: numeric(packet.water_height_cm, ' cm') },
  ]
}

const rawSensorFields: { key: keyof Esp32RawReadings; label: string }[] = [
  { key: 'water_temperature', label: 'Water temperature' },
  { key: 'ph', label: 'pH probe' },
  { key: 'tds', label: 'TDS probe' },
  { key: 'ultrasonic', label: 'Ultrasonic water level' },
  { key: 'air_temperature', label: 'Air temperature' },
  { key: 'humidity', label: 'Humidity' },
]

function rawStatus(reading: Esp32RawSensorReading | null | undefined): string {
  if (!reading) return 'Not reported'
  switch (reading.status) {
    case 'ok': return 'Reading OK'
    case 'not_configured': return 'Not configured'
    case 'disconnected': return 'Disconnected'
    case 'timeout': return 'Timeout'
    case 'read_error': return 'Read failure'
  }
}

function rawValue(reading: Esp32RawSensorReading | null | undefined): string {
  if (!reading || reading.value == null) return '—'
  const units: Record<string, string> = {
    adc_count: 'ADC counts',
    microseconds: 'µs',
    celsius: '°C',
    percent: '%',
    sensor_ticks: 'sensor ticks',
    volts: 'V',
  }
  return `${reading.value} ${reading.unit ? units[reading.unit] : ''}`.trim()
}

type SimpleReading = {
  label: string
  value: string
  recordedAt: string
  origin: 'hardware' | 'simulator'
  activeWindowMs: number
  rawFaultAt?: string
}

function displaySensorName(sensor: DashboardSensor): string {
  const field = sensor.hardware_identifier?.split(':').at(-1)
  const nameByField: Record<string, string> = {
    water_temp_c: 'Water temperature',
    ph: 'pH',
    tds_ppm: 'TDS',
    water_level_pct: 'Water level',
    water_height_cm: 'Water height',
    distance_cm: 'Ultrasonic distance',
    air_temp_c: 'Air temperature',
    humidity_pct: 'Air humidity',
  }
  if (field && nameByField[field]) return nameByField[field]
  switch (sensor.sensor_type) {
    case 'water_temperature': return 'Water temperature'
    case 'air_temperature': return 'Air temperature'
    case 'humidity': return 'Air humidity'
    case 'ph': return 'pH'
    case 'tds': return 'TDS'
    case 'water_level': return sensor.name || 'Water level'
    default: return sensor.name
  }
}

function simplePacketMetrics(packet: Esp32SensorPacket, receivedAt: string): SimpleReading[] {
  const candidates = [
    { label: 'Water temperature', value: packet.water_temp_c, unit: '°C', rawKey: 'water_temperature' },
    { label: 'Water level', value: packet.water_level_pct, unit: '%', rawKey: 'ultrasonic' },
    { label: 'Water height', value: packet.water_height_cm, unit: 'cm', rawKey: 'ultrasonic' },
    { label: 'Ultrasonic distance', value: packet.distance_cm, unit: 'cm', rawKey: 'ultrasonic' },
    { label: 'Air temperature', value: packet.air_temp_c, unit: '°C', rawKey: 'air_temperature' },
    { label: 'Air humidity', value: packet.humidity_pct, unit: '%', rawKey: 'humidity' },
  ] as const

  return candidates.flatMap(({ label, value, unit, rawKey }) => {
    const raw = packet.raw_readings?.[rawKey]
    if (value === null || !Number.isFinite(value) || (raw && raw.status !== 'ok')) return []
    return [{
      label,
      value: `${value.toFixed(unit === '%' ? 1 : 2)} ${unit}`,
      recordedAt: receivedAt,
      origin: 'hardware' as const,
      activeWindowMs: 45_000,
    }]
  })
}

function composeSimpleReadings(
  packet: Esp32Telemetry | null,
  overview: SystemSensorOverview | null,
): SimpleReading[] {
  const byLabel = new Map<string, SimpleReading>()
  // The packet archive can supply readings without a configured database bridge.
  if (packet) {
    for (const metric of simplePacketMetrics(packet.packet, packet.received_at)) {
      byLabel.set(metric.label, metric)
    }
  }
  if (overview) {
    const sensors = new Map(overview.sensors.map(sensor => [sensor.id, sensor]))
    for (const reading of overview.latestReadings) {
      const sensor = sensors.get(reading.sensor_id)
      if (!sensor || !sensor.is_enabled || reading.quality_status !== 'good') continue
      if (sensor.sensor_type === 'ph' || sensor.sensor_type === 'tds') {
        // Only registered readings with server-side calibration approval qualify.
        if (sensor.calibration_status !== 'verified') continue
      }
      const value = Number(reading.value_numeric)
      if (!Number.isFinite(value)) continue
      const label = displaySensorName(sensor)
      const metric: SimpleReading = {
        label,
        value: `${value.toFixed(sensor.unit === 'ppm' ? 0 : 2)} ${reading.unit}`,
        recordedAt: reading.recorded_at,
        origin: sensor.is_simulated || reading.source === 'simulator' ? 'simulator' : 'hardware',
        activeWindowMs: Math.max(45_000, Math.min(sensor.sampling_interval_seconds * 3_000, 120_000)),
      }
      const current = byLabel.get(label)
      if (!current || Date.parse(metric.recordedAt) > Date.parse(current.recordedAt)) {
        byLabel.set(label, metric)
      }
    }
  }

  // If the newest ESP32 packet reports that a physical read failed, an old
  // registered value must not masquerade as an active device measurement.
  if (packet?.packet.raw_readings) {
    const faults: Record<string, string[]> = {
      water_temperature: ['Water temperature'],
      ultrasonic: ['Water level', 'Water height', 'Ultrasonic distance'],
      air_temperature: ['Air temperature'],
      humidity: ['Air humidity'],
      ph: ['pH'],
      tds: ['TDS'],
    }
    for (const [rawKey, labels] of Object.entries(faults)) {
      const raw = packet.packet.raw_readings[rawKey as keyof Esp32RawReadings]
      if (raw && raw.status !== 'ok') {
        for (const label of labels) {
          const current = byLabel.get(label)
          if (current && Date.parse(current.recordedAt) <= Date.parse(packet.received_at)) {
            byLabel.set(label, { ...current, rawFaultAt: packet.received_at })
          }
        }
      }
    }
  }

  return [...byLabel.values()].sort((left, right) => left.label.localeCompare(right.label))
}

function simpleReadingState(reading: SimpleReading, nowMs: number): 'Active' | 'Last saved' | 'Simulated' {
  if (reading.origin === 'simulator') return 'Simulated'
  const ageMs = nowMs - Date.parse(reading.recordedAt)
  const faultIsNewer = reading.rawFaultAt && Date.parse(reading.rawFaultAt) >= Date.parse(reading.recordedAt)
  return !faultIsNewer && Number.isFinite(ageMs) && ageMs >= -10_000 && ageMs <= reading.activeWindowMs
    ? 'Active'
    : 'Last saved'
}

/**
 * Standalone, read-only view. It does not register values as calibrated
 * sensor readings or send any commands to pumps/actuators.
 */
export function Esp32TelemetryPanel({ systemId, demoPackets, mode = 'details' }: Props) {
  const [packets, setPackets] = useState<Esp32Telemetry[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [nowMs, setNowMs] = useState(() => Date.now())
  const [registeredOverview, setRegisteredOverview] = useState<SystemSensorOverview | null>(null)
  const [registeredStatus, setRegisteredStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  useEffect(() => {
    // Demo preview bypasses API polling entirely.
    if (demoPackets !== undefined) return

    let active = true
    let busy = false
    // Parent keys this widget by systemId; remounting resets its state.
    const refresh = async () => {
      if (busy) return
      busy = true
      try {
        const next = await listEsp32Telemetry(systemId)
        if (active) {
          setPackets(next)
          setStatus('ready')
        }
      } catch {
        if (active) setStatus('error')
      } finally {
        busy = false
      }
    }

    void refresh()
    const timer = window.setInterval(() => {
      setNowMs(Date.now())
      void refresh()
    }, 10000)

    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [systemId, demoPackets])

  // Registered sensor history is an independent source of measurements.
  // This makes the Sensors page usable even if ESP32 packet archiving and
  // registered-reading persistence were configured at different times.
  useEffect(() => {
    if (mode !== 'simple' || demoPackets !== undefined) return

    let active = true
    let busy = false
    const refreshRegistered = async () => {
      if (busy) return
      busy = true
      try {
        const next = await loadSystemSensorOverview(systemId)
        if (active) {
          setRegisteredOverview(next)
          setRegisteredStatus('ready')
        }
      } catch {
        if (active) setRegisteredStatus('error')
      } finally {
        busy = false
      }
    }
    void refreshRegistered()
    const timer = window.setInterval(() => { void refreshRegistered() }, 10000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [systemId, mode, demoPackets])

  const displayedPackets = demoPackets ?? packets
  const displayedStatus = demoPackets !== undefined ? 'ready' : status
  const latest = displayedPackets[0] ?? null
  const packet = latest?.packet
  const connection = demoPackets !== undefined
    ? { state: 'unknown', label: 'Demo preview', detail: 'Sample data only; no physical ESP32 connection checked.' }
    : signalHealth(latest, displayedStatus, nowMs)

  const readings = composeSimpleReadings(latest, registeredOverview)
  if (mode === 'simple') {
    const successfulSource = displayedStatus === 'ready' || registeredStatus === 'ready'
    const hasCurrentData = readings.some(reading => simpleReadingState(reading, nowMs) === 'Active')

    return (
      <section className="esp32-telemetry" aria-label="Current sensor readings">
        <div className="esp32-telemetry__header">
          <div>
            <p className="eyebrow">Monitoring</p>
            <h2>Sensor readings</h2>
          </div>
          <span>Refreshes every 10 seconds</span>
        </div>
        <div className="esp32-telemetry__connection" data-state={hasCurrentData ? 'connected' : 'stale'} role="status" aria-live="polite">
          <span className="esp32-telemetry__connection-dot" aria-hidden="true" />
          <div>
            <strong>{hasCurrentData ? 'Receiving recent measurements' : 'No current measurements'}</strong>
            <p>{readings.length > 0
              ? 'Saved measurements remain visible when the device stops reporting.'
              : 'No saved sensor measurements are available for this system.'}</p>
          </div>
        </div>
        {displayedStatus === 'loading' && registeredStatus === 'loading' && (
          <p role="status">Loading sensor readings...</p>
        )}
        {displayedStatus === 'error' && registeredStatus === 'error' && (
          <p role="alert">Unable to load sensor readings from the backend. Check the API connection.</p>
        )}
        {readings.length > 0 && (
          <div className="esp32-telemetry__grid">
            {readings.map(reading => {
              const state = simpleReadingState(reading, nowMs)
              return (
                <article className="esp32-telemetry__metric" key={reading.label}>
                  <span>{reading.label}</span>
                  <strong>{reading.value}</strong>
                  <span className={state === 'Active'
                    ? 'sensor-state sensor-state--enabled'
                    : 'sensor-state sensor-state--disabled'}>
                    {state}
                  </span>
                  <span>Recorded: {timestamp(reading.recordedAt)}</span>
                </article>
              )
            })}
          </div>
        )}
        {successfulSource && readings.length === 0 && (
          <p>No saved sensor values yet. Check that the selected system is receiving ESP32 packets or registered sensor readings.</p>
        )}
        <p className="data-note">
          Active means a recent usable measurement, not proof of probe accuracy.
          Unverified pH and TDS estimates are not displayed as calibrated values.
        </p>
      </section>
    )
  }

  return (
    <section className="esp32-telemetry" aria-label="ESP32 device telemetry">
      <div className="esp32-telemetry__header">
        <div>
          <p className="eyebrow">ESP32 device telemetry</p>
          <h2>ESP32 sensor readings</h2>
        </div>
        <span>Saved packet history · Refreshes every 10 seconds</span>
      </div>

      <div className="esp32-telemetry__connection" data-state={connection.state} role="status" aria-live="polite">
        <span className="esp32-telemetry__connection-dot" aria-hidden="true" />
        <div>
          <strong>ESP32: {connection.label}</strong>
          <p>{connection.detail}</p>
        </div>
      </div>

      {displayedStatus === 'loading' && (
        <p role="status">Loading ESP32 sensor packets...</p>
      )}
      {displayedStatus === 'error' && (
        <p role="alert">Cannot refresh ESP32 data. Previously saved values may be stale.</p>
      )}
      {displayedStatus === 'ready' && latest === null && (
        <p>No ESP32 packets saved for this system yet.</p>
      )}

      {latest !== null && packet !== undefined && (
        <>
          <p className="esp32-telemetry__meta">
            Device: <strong>{packet.device_id}</strong> · Sequence {packet.sequence}
            {' · '}Uptime {packet.uptime_ms} ms · Received {timestamp(latest.received_at)}
          </p>

          <div className="esp32-telemetry__grid">
            {fields(packet).map(({ label, value }) => (
              <article className="esp32-telemetry__metric" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </div>

          <div className="esp32-telemetry__diagnostics">
            <h3>Unverified sensor diagnostics</h3>
            <p>
              pH voltage: {numeric(packet.ph_voltage_v, ' V', 3)} · Unverified estimate:
              {' '}{numeric(packet.ph_unverified_estimate)} (not a valid calibrated pH reading)
            </p>
            <p>
              TDS voltage: {numeric(packet.tds_voltage_v, ' V', 3)} · Unverified estimate:
              {' '}{numeric(packet.tds_unverified_ppm, ' ppm', 0)} (not calibrated)
            </p>
            <p>
              These estimates are stored for troubleshooting only. They are not used
              for water-quality alerts or automatic actuator control.
            </p>
          </div>

          <div className="esp32-telemetry__diagnostics">
            <h3>Raw USB readings and sensor status</h3>
            <p>
              Status is reported by ESP32 firmware, never inferred from a null measurement.
              Uncalibrated pH/TDS values can be null even when their raw sensors work.
            </p>
            {packet.raw_readings ? (
              <div className="esp32-telemetry__history">
                <table>
                  <thead>
                    <tr><th>Sensor</th><th>Read status</th><th>Raw reading</th><th>Device fault code</th></tr>
                  </thead>
                  <tbody>
                    {rawSensorFields.map(({ key, label }) => {
                      const reading = packet.raw_readings?.[key]
                      return (
                        <tr key={key}>
                          <td>{label}</td>
                          <td>{rawStatus(reading)}</td>
                          <td>{rawValue(reading)}</td>
                          <td>{reading?.error_code ?? '—'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>No raw diagnostics in this packet. Update the ESP32 firmware to report
                raw_readings; this does not prove the sensor is faulty.</p>
            )}
          </div>

          <h3>Recent packets</h3>
          <div className="esp32-telemetry__history">
            <table>
              <thead>
                <tr><th>Received</th><th>Device</th><th>Sequence</th><th>Water °C</th><th>pH status</th><th>TDS status</th><th>Raw pH</th><th>Raw TDS</th><th>Ultrasonic status</th></tr>
              </thead>
              <tbody>
                {displayedPackets.map((item) => (
                  <tr key={item.id}>
                    <td>{timestamp(item.received_at)}</td>
                    <td>{item.packet.device_id}</td>
                    <td>{item.packet.sequence}</td>
                    <td>{numeric(item.packet.water_temp_c, '', 2)}</td>
                    <td>{item.packet.ph_calibrated ? 'Calibrated' : 'Unverified'}</td>
                    <td>{item.packet.tds_calibrated ? 'Calibrated' : 'Unverified'}</td>
                    <td>{rawValue(item.packet.raw_readings?.ph)}</td>
                    <td>{rawValue(item.packet.raw_readings?.tds)}</td>
                    <td>{rawStatus(item.packet.raw_readings?.ultrasonic)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
