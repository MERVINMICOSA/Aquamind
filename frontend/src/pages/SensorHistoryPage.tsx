import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
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
type MeasurementField = Exclude<Esp32HistoryField, 'all'>

const FIELDS: {
  value: MeasurementField
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
}

const DEFAULT_FILTERS: HistoryFilters = {
  field: 'all',
  from: '',
  to: '',
}

function localStartIso(day: string): string | undefined {
  if (!day) return undefined
  const date = new Date(`${day}T00:00:00`)
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString()
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
  field: MeasurementField,
): { value: number | null; detail: string } {
  const spec = FIELDS.find(candidate => candidate.value === field)
  if (!spec) return { value: null, detail: 'Unsupported sensor' }

  const raw = item.packet.raw_readings?.[spec.rawKey]
  if (raw && raw.status !== 'ok') {
    return { value: null, detail: `Sensor read: ${raw.status.replaceAll('_', ' ')}` }
  }

  const value = item.packet[field]
  if (value === null || !Number.isFinite(value)) {
    if (field === 'ph' && !item.packet.ph_calibrated) {
      return { value: null, detail: 'Not calibrated' }
    }
    if (field === 'tds_ppm' && !item.packet.tds_calibrated) {
      return { value: null, detail: 'Not calibrated' }
    }
    return { value: null, detail: 'No reading' }
  }

  // Firmware flags alone do not prove independently verified calibration.
  if (field === 'ph' || field === 'tds_ppm') {
    const claimed = field === 'ph' ? item.packet.ph_calibrated : item.packet.tds_calibrated
    if (!claimed) return { value: null, detail: 'Not calibrated' }
    return { value, detail: 'Device reported — not independently verified' }
  }
  return { value, detail: 'Archived ESP32 reading' }
}

function displayValue(
  measurement: ReturnType<typeof packetMeasurement>,
  field: MeasurementField,
): string {
  if (measurement.value === null) {
    return measurement.detail === 'No reading' ? '—' : measurement.detail
  }
  const config = FIELDS.find(candidate => candidate.value === field)
  const digits = field === 'tds_ppm' ? 0 : 2
  return `${measurement.value.toFixed(digits)} ${config?.unit ?? ''}`.trim()
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
      // The operator no longer configures a system ID in History. Prefer the
      // active AquaMind system, falling back to the first configured system.
      setSystemId((data.find(system => system.is_active) ?? data[0])?.id ?? '')
      setSystemsStatus('ready')
    }).catch(() => {
      if (active) setSystemsStatus('error')
    })
    return () => { active = false }
  }, [])

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
    // Keep the first page dynamic. Older pages stay fixed while browsing.
    const interval = page === 0
      ? window.setInterval(() => { void refresh() }, 15000)
      : null
    return () => {
      active = false
      if (interval !== null) window.clearInterval(interval)
    }
  }, [systemId, applied, page, queryKey])

  const visible = loaded?.key === queryKey ? loaded : null
  const selectedField = applied.field === 'all'
    ? null
    : FIELDS.find(item => item.value === applied.field) ?? null
  const items = visible?.data.items ?? []
  const chartRows: DashboardSensorReading[] = selectedField === null
    ? []
    : items.flatMap(item => {
        const measurement = packetMeasurement(item, selectedField.value)
        if (measurement.value === null) return []
        return [{
          id: item.id,
          sensor_id: selectedField.value,
          recorded_at: item.received_at,
          value_numeric: measurement.value,
          unit: selectedField.unit,
          quality_status: selectedField.diagnostic ? 'unverified' : 'good',
          source: 'hardware',
          sequence_number: item.packet.sequence,
          created_at: item.received_at,
        }]
      })

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (draft.from && draft.to && draft.from > draft.to) {
      setValidationError('Start date cannot be after end date.')
      return
    }
    setValidationError(null)
    setPage(0)
    setApplied({ ...draft })
    setRefreshCounter(value => value + 1)
  }

  const system = systems.find(item => item.id === systemId)

  return (
    <section className="section-page">
      <header className="sensors-page-heading">
        <div>
          <p className="eyebrow">Historical monitoring</p>
          <h1>Sensor History</h1>
          <p className="page-description">
            View all saved ESP32 sensor readings together or choose one sensor.
            Dates use your browser's local timezone; timestamps reflect Raspberry Pi receipt time.
          </p>
        </div>
        <Link to="/sensors" className="sensor-detail-link">Current sensors</Link>
      </header>

      {systemsStatus === 'loading' && <p role="status">Loading aquaponics systems...</p>}
      {systemsStatus === 'error' && <p role="alert">Unable to load AquaMind systems.</p>}
      {systemsStatus === 'ready' && systems.length === 0 && (
        <p className="empty-state">No aquaponics system is configured yet.</p>
      )}
      {system && (
        <>
          <p className="page-description">
            Showing history for <strong>{system.name}</strong>
          </p>
          <form className="sensor-history-filters surface-panel" onSubmit={submitSearch}>
            <label>
              Sensor
              <select
                value={draft.field}
                onChange={event => setDraft(current => ({
                  ...current, field: event.target.value as Esp32HistoryField,
                }))}
              >
                <option value="all">All data</option>
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

          {(applied.field === 'all' || selectedField?.diagnostic) && (
            <p className="sensor-history-warning" role="note">
              Archived pH/TDS values are device-reported and not independently
              verified by AquaMind. Unverified estimates are not displayed as calibrated values.
            </p>
          )}

          {!visible && status !== 'error' && <p role="status">Searching saved readings...</p>}
          {!visible && status === 'error' && <p role="alert">{errorMessage}</p>}
          {visible && (
            <section className="sensor-history-results surface-panel">
              <div className="sensor-history-results-heading">
                <div>
                  <h2>{selectedField?.label ?? 'All sensor data'} history</h2>
                  <p className="page-description">
                    {visible.data.total.toLocaleString()} matching saved {selectedField === null ? 'packets' : 'readings'}
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
                  {selectedField !== null && (
                    <div className="sensor-history-chart">
                      <h3>Trend for this page</h3>
                      <SensorTrendChart readings={chartRows} unit={selectedField.unit} />
                    </div>
                  )}
                  {selectedField === null && (
                    <p className="page-description">
                      All data shows each archived packet as one row, with a column
                      for each sensor. Choose an individual sensor to view its trend.
                    </p>
                  )}
                  <div className="sensor-history-table-wrap">
                    <table className="sensor-history-table">
                      <thead>
                        <tr>
                          <th scope="col">Received</th>
                          {selectedField === null
                            ? FIELDS.map(field => (
                                <th scope="col" key={field.value}>{field.label}</th>
                              ))
                            : <>
                                <th scope="col">Reading</th>
                                <th scope="col">Status</th>
                              </>}
                        </tr>
                      </thead>
                      <tbody>
                        {items.map(item => (
                          <tr key={item.id}>
                            <td>{formatTime(item.received_at)}</td>
                            {selectedField === null
                              ? FIELDS.map(field => {
                                  const measurement = packetMeasurement(item, field.value)
                                  return (
                                    <td key={field.value} title={measurement.detail}>
                                      {displayValue(measurement, field.value)}
                                    </td>
                                  )
                                })
                              : (() => {
                                  const measurement = packetMeasurement(item, selectedField.value)
                                  return (
                                    <>
                                      <td>{displayValue(measurement, selectedField.value)}</td>
                                      <td>{measurement.detail}</td>
                                    </>
                                  )
                                })()}
                          </tr>
                        ))}
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
                Past data remains available when the ESP32 is offline. Only the
                first results page refreshes automatically every 15 seconds.
                Pagination counts saved packets, not individual sensor values.
              </p>
            </section>
          )}
        </>
      )}
    </section>
  )
}
