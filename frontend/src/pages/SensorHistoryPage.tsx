import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listSystems } from '../services/dashboardService'
import {
  searchEsp32Telemetry,
  type Esp32HistoryField,
  type Esp32HistorySearchResult,
} from '../services/esp32TelemetryService'
import type { AquaponicsSystem, DashboardSensorReading } from '../types/dashboard'
import type { Esp32RawReadings, Esp32Telemetry } from '../types/esp32Telemetry'
import { SensorTrendChart } from '../components/sensors/SensorTrendChart'
import './SensorHistoryPage.css'

const PAGE_SIZE = 25

const FIELDS: {
  value: Esp32HistoryField
  label: string
  unit: string
  rawKey: keyof Esp32RawReadings
  diagnostic?: boolean
}[] = [
  { value: 'water_temp_c', label: 'Water temperature', unit: '°C', rawKey: 'water_temperature' },
  { value: 'air_temp_c', label: 'Air temperature', unit: '°C', rawKey: 'air_temperature' },
  { value: 'humidity_pct', label: 'Humidity', unit: '%', rawKey: 'humidity' },
  { value: 'water_level_pct', label: 'Water level', unit: '%', rawKey: 'ultrasonic' },
  { value: 'water_height_cm', label: 'Water height', unit: 'cm', rawKey: 'ultrasonic' },
  { value: 'distance_cm', label: 'Ultrasonic distance', unit: 'cm', rawKey: 'ultrasonic' },
  { value: 'ph', label: 'pH (device reported)', unit: 'pH', rawKey: 'ph', diagnostic: true },
  { value: 'tds_ppm', label: 'TDS (device reported)', unit: 'ppm', rawKey: 'tds', diagnostic: true },
]

type HistoryFilters = {
  field: Esp32HistoryField
  from: string
  to: string
  min: string
  max: string
}

const DEFAULT_FILTERS: HistoryFilters = {
  field: 'water_temp_c',
  from: '',
  to: '',
  min: '',
  max: '',
}

function localStartIso(day: string): string | undefined {
  if (!day) return undefined
  const date = new Date(`${day}T00:00:00`)
  if (Number.isNaN(date.getTime())) return undefined
  return date.toISOString()
}

function localEndExclusiveIso(day: string): string | undefined {
  if (!day) return undefined
  const date = new Date(`${day}T00:00:00`)
  if (Number.isNaN(date.getTime())) return undefined
  date.setDate(date.getDate() + 1)
  return date.toISOString()
}

function formatTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleString()
}

function packetMeasurement(
  item: Esp32Telemetry,
  field: Esp32HistoryField,
): { value: number | null; detail: string } {
  const spec = FIELDS.find(candidate => candidate.value === field)
  if (!spec) return { value: null, detail: 'Unsupported field' }

  const raw = item.packet.raw_readings?.[spec.rawKey]
  if (raw && raw.status !== 'ok') {
    return { value: null, detail: `Sensor read: ${raw.status.replaceAll('_', ' ')}` }
  }

  const value = item.packet[field]
  if (value === null || !Number.isFinite(value)) {
    return { value: null, detail: 'No usable reading' }
  }

  // Firmware flags are diagnostic claims, not audited AquaMind calibration.
  if (field === 'ph' || field === 'tds_ppm') {
    const claimed = field === 'ph' ? item.packet.ph_calibrated : item.packet.tds_calibrated
    if (!claimed) return { value: null, detail: 'Device has not calibrated this reading' }
    return { value, detail: 'Device reported — not independently verified' }
  }
  return { value, detail: 'Archived ESP32 reading' }
}

export function SensorHistoryPage() {
  const [systems, setSystems] = useState<AquaponicsSystem[]>([])
  const [systemId, setSystemId] = useState('')
  const [systemsStatus, setSystemsStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  const [draft, setDraft] = useState<HistoryFilters>(DEFAULT_FILTERS)
  const [applied, setApplied] = useState<HistoryFilters>(DEFAULT_FILTERS)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const [refreshCounter, setRefreshCounter] = useState(0)

  const [loaded, setLoaded] = useState<{
    key: string
    data: Esp32HistorySearchResult
    checkedAt: string
  } | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void listSystems().then(data => {
      if (!active) return
      setSystems(data)
      setSystemId(data[0]?.id ?? '')
      setSystemsStatus('ready')
    }).catch(() => {
      if (active) setSystemsStatus('error')
    })
    return () => { active = false }
  }, [])

  // Identity of the actual result set, including the chosen system and page.
  // Prevent old-system rows from appearing while a new search is loading.
  const queryKey = JSON.stringify([systemId, applied, page, refreshCounter])
  useEffect(() => {
    if (!systemId) return
    let active = true
    let busy = false

    const refresh = async () => {
      if (busy) return
      busy = true
      try {
        const data = await searchEsp32Telemetry({
          systemId,
          field: applied.field,
          startAt: localStartIso(applied.from),
          endAt: localEndExclusiveIso(applied.to),
          minValue: applied.min === '' ? undefined : Number(applied.min),
          maxValue: applied.max === '' ? undefined : Number(applied.max),
          offset: page * PAGE_SIZE,
          limit: PAGE_SIZE,
        })
        if (!active) return
        setLoaded({ key: queryKey, data, checkedAt: new Date().toISOString() })
        setStatus('ready')
        setErrorMessage(null)
      } catch {
        if (!active) return
        setStatus('error')
        setErrorMessage('Unable to search saved readings. Check the API connection.')
      } finally {
        busy = false
      }
    }

    void refresh()
    // The first page follows incoming saved packets; other pages stay stable.
    const interval = page === 0
      ? window.setInterval(() => { void refresh() }, 15000)
      : null
    return () => {
      active = false
      if (interval !== null) window.clearInterval(interval)
    }
  }, [systemId, applied, page, queryKey])

  const visible = loaded?.key === queryKey ? loaded : null
  const config = FIELDS.find(item => item.value === applied.field) ?? FIELDS[0]!
  const items = visible?.data.items ?? []
  const chartRows = useMemo<DashboardSensorReading[]>(() => {
    return items.flatMap(item => {
      const measurement = packetMeasurement(item, config.value)
      if (measurement.value === null) return []
      return [{
        id: item.id,
        sensor_id: config.value,
        recorded_at: item.received_at,
        value_numeric: measurement.value,
        unit: config.unit,
        quality_status: config.diagnostic ? 'unverified' : 'good',
        source: 'hardware',
        sequence_number: item.packet.sequence,
        created_at: item.received_at,
      }]
    })
  }, [items, config.value, config.unit, config.diagnostic])

  function submitSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (draft.from && draft.to && draft.from > draft.to) {
      setValidationError('Start date cannot be after end date.')
      return
    }
    if (
      (draft.min !== '' && !Number.isFinite(Number(draft.min))) ||
      (draft.max !== '' && !Number.isFinite(Number(draft.max))) ||
      (draft.min !== '' && draft.max !== '' && Number(draft.min) > Number(draft.max))
    ) {
      setValidationError('Enter valid minimum and maximum values (minimum must not exceed maximum).')
      return
    }
    setValidationError(null)
    setPage(0)
    setApplied({ ...draft })
    setRefreshCounter(value => value + 1)
  }

  return (
    <section className="section-page">
      <header className="sensors-page-heading">
        <div>
          <p className="eyebrow">Historical monitoring</p>
          <h1>Sensor History</h1>
          <p className="page-description">
            Search past measurements saved by AquaMind. Dates use your browser's
            local timezone; records are timestamped when the Raspberry Pi received them.
          </p>
        </div>
        <Link to="/sensors" className="sensor-detail-link">Current sensors</Link>
      </header>

      {systemsStatus === 'loading' && <p role="status">Loading aquaponics systems...</p>}
      {systemsStatus === 'error' && <p role="alert">Unable to load AquaMind systems.</p>}
      {systemsStatus === 'ready' && systems.length === 0 && (
        <p className="empty-state">No aquaponics system is configured yet.</p>
      )}
      {systems.length > 0 && (
        <>
          <form className="sensor-history-filters surface-panel" onSubmit={submitSearch}>
            <label>
              Aquaponics system
              <select
                value={systemId}
                onChange={event => { setSystemId(event.target.value); setPage(0) }}
              >
                {systems.map(system => (
                  <option value={system.id} key={system.id}>{system.name}</option>
                ))}
              </select>
            </label>
            <label>
              Sensor
              <select
                value={draft.field}
                onChange={event => setDraft(current => ({
                  ...current, field: event.target.value as Esp32HistoryField,
                }))}
              >
                {FIELDS.map(field => (
                  <option value={field.value} key={field.value}>{field.label}</option>
                ))}
              </select>
            </label>
            <label>
              From date
              <input
                type="date" value={draft.from}
                onChange={event => setDraft(current => ({ ...current, from: event.target.value }))}
              />
            </label>
            <label>
              To date
              <input
                type="date" value={draft.to}
                onChange={event => setDraft(current => ({ ...current, to: event.target.value }))}
              />
            </label>
            <label>
              Minimum value
              <input
                type="number" step="any" placeholder="Any"
                value={draft.min}
                onChange={event => setDraft(current => ({ ...current, min: event.target.value }))}
              />
            </label>
            <label>
              Maximum value
              <input
                type="number" step="any" placeholder="Any"
                value={draft.max}
                onChange={event => setDraft(current => ({ ...current, max: event.target.value }))}
              />
            </label>
            <div className="sensor-history-actions">
              <button type="submit">Search readings</button>
              <button type="button" onClick={() => {
                setDraft(DEFAULT_FILTERS)
                setApplied(DEFAULT_FILTERS)
                setPage(0)
                setValidationError(null)
                setRefreshCounter(value => value + 1)
              }}>Clear filters</button>
              <button type="button" onClick={() => setRefreshCounter(value => value + 1)}>
                Refresh
              </button>
            </div>
            {validationError && <p role="alert">{validationError}</p>}
          </form>

          {config.diagnostic && (
            <p className="sensor-history-warning" role="note">
              pH/TDS values in this archive are reported by ESP32 firmware.
              They are not independently verified by the AquaMind calibration database
              and must not be used as validated water-quality measurements.
            </p>
          )}

          {!visible && status !== 'error' && <p role="status">Searching saved readings...</p>}
          {!visible && status === 'error' && <p role="alert">{errorMessage}</p>}
          {visible && (
            <section className="sensor-history-results surface-panel">
              <div className="sensor-history-results-heading">
                <div>
                  <h2>{config.label} history</h2>
                  <p className="page-description">
                    {visible.data.total.toLocaleString()} matching saved readings
                    {' · '}Updated {formatTime(visible.checkedAt)}
                  </p>
                </div>
                <span>Page {page + 1} of {Math.max(1, Math.ceil(visible.data.total / PAGE_SIZE))}</span>
              </div>
              {status === 'error' && <p role="alert">{errorMessage} Displaying the last loaded results.</p>}
              {items.length === 0 ? (
                <div className="empty-state">
                  <p>No saved readings match this search.</p>
                  <p>Try a wider date range or a different sensor.</p>
                </div>
              ) : (
                <>
                  <div className="sensor-history-chart">
                    <h3>Trend for this page</h3>
                    <SensorTrendChart readings={chartRows} unit={config.unit} />
                  </div>
                  <div className="sensor-history-table-wrap">
                    <table className="sensor-history-table">
                      <thead>
                        <tr>
                          <th scope="col">Received</th>
                          <th scope="col">Reading</th>
                          <th scope="col">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {items.map(item => {
                          const measurement = packetMeasurement(item, config.value)
                          return (
                            <tr key={item.id}>
                              <td>{formatTime(item.received_at)}</td>
                              <td>{measurement.value === null
                                ? '—'
                                : `${measurement.value.toFixed(config.value === 'tds_ppm' ? 0 : 2)} ${config.unit}`}</td>
                              <td>{measurement.detail}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
              <div className="sensor-history-pagination">
                <button
                  type="button" disabled={page === 0}
                  onClick={() => setPage(current => Math.max(0, current - 1))}
                >Previous page</button>
                <button
                  type="button" disabled={(page + 1) * PAGE_SIZE >= visible.data.total}
                  onClick={() => setPage(current => current + 1)}
                >Next page</button>
              </div>
              <p className="page-description">
                History remains available when the ESP32 is offline. Only the first
                results page auto-refreshes every 15 seconds. The trend shows
                measurements from the current page, not the entire archive.
              </p>
            </section>
          )}
        </>
      )}
    </section>
  )
}
