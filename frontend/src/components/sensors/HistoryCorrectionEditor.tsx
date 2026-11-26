import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { apiRequest } from '../../services/apiClient'
import type { Esp32Telemetry } from '../../types/esp32Telemetry'

const FIELDS = [
  ['water_temp_c', 'Water temperature (°C)', -10, 90, 'water_temperature'],
  ['air_temp_c', 'Air temperature (°C)', -50, 90, 'air_temperature'],
  ['humidity_pct', 'Humidity (%)', 0, 100, 'humidity'],
  ['water_level_pct', 'Water level (%)', 0, 100, 'ultrasonic'],
  ['water_height_cm', 'Water height (cm)', 0, 100000, 'ultrasonic'],
  ['distance_cm', 'Ultrasonic distance (cm)', 0, 100000, 'ultrasonic'],
  ['ph', 'pH', 0, 14, 'ph'],
  ['tds_ppm', 'TDS (ppm)', 0, 100000, 'tds'],
] as const

type Field = typeof FIELDS[number][0]
type Correction = {
  id: string
  field: Field
  original_value: number
  corrected_value: number
  reason: string
  evidence: string
  recorded_by: string
  created_at: string
}

function available(item: Esp32Telemetry, spec: typeof FIELDS[number]) {
  const value = item.packet[spec[0]]
  const raw = item.packet.raw_readings?.[spec[4]]
  return typeof value === 'number' && Number.isFinite(value)
    && value >= spec[2] && value <= spec[3]
    && (!raw || raw.status === 'ok')
    && (spec[0] !== 'ph' || item.packet.ph_calibrated)
    && (spec[0] !== 'tds_ppm' || item.packet.tds_calibrated)
}

export function HistoryCorrectionEditor({ item, onClose }: {
  item: Esp32Telemetry
  onClose: () => void
}) {
  const fields = FIELDS.filter(spec => available(item, spec))
  const [field, setField] = useState<Field | ''>(fields[0]?.[0] ?? '')
  const [value, setValue] = useState('')
  const [reason, setReason] = useState('')
  const [evidence, setEvidence] = useState('')
  const [records, setRecords] = useState<Correction[]>([])
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const endpoint = 'esp32/telemetry/' + encodeURIComponent(item.id)
    + '/corrections?system_id=' + encodeURIComponent(item.system_id)
  const selected = fields.find(spec => spec[0] === field)

  useEffect(() => {
    let active = true
    void apiRequest<Correction[]>(endpoint).then(data => {
      if (active) setRecords(data)
    }).catch(() => {
      if (active) setLoadFailed(true)
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [endpoint])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (saving || loading || loadFailed || !selected) return
    const number = Number(value)
    if (!value.trim() || !Number.isFinite(number) || number < selected[2]
      || number > selected[3] || number === item.packet[selected[0]]
      || !reason.trim() || !evidence.trim()) {
      setError('Enter a different, supported numeric value and document the reason and evidence.')
      return
    }
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const saved = await apiRequest<Correction>(endpoint, {
        method: 'POST',
        body: JSON.stringify({
          field, corrected_value: number, reason: reason.trim(), evidence: evidence.trim(),
        }),
      })
      setRecords(previous => [saved, ...previous].slice(0, 100))
      setValue('')
      setReason('')
      setEvidence('')
      setMessage('Correction saved to PostgreSQL as a separate, unverified manual proposal.')
    } catch {
      setError('Correction could not be saved. Check administrator permissions and the API connection.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="surface-panel" aria-label="Reading correction editor">
      <h3>Edit reading — documented correction</h3>
      <p>Received: {new Date(item.received_at).toLocaleString()} · {item.packet.device_id}</p>
      <p>Original measurements, receipt time, and device identifiers remain unchanged.
        Proposed corrections require evidence and are not verified sensor data.</p>
      <button type="button" onClick={onClose} disabled={saving}>Close editor</button>
      {loading && <p role="status">Loading saved corrections…</p>}
      {loadFailed && <p role="alert">Unable to load correction history. Close and reopen to retry.</p>}
      {!fields.length && <p>There are no valid recorded measurements to correct.</p>}
      {!!fields.length && (
        <form className="sensor-history-filters" onSubmit={save}>
          <label>Sensor
            <select value={field} disabled={saving} onChange={event => {
              setField(event.target.value as Field)
              setValue('')
              setError('')
            }}>
              {fields.map(spec => <option key={spec[0]} value={spec[0]}>{spec[1]}</option>)}
            </select>
          </label>
          {selected && <p>Original value: <strong>{item.packet[selected[0]]}</strong></p>}
          <label>Proposed corrected value
            <input type="number" step="any" min={selected?.[2]} max={selected?.[3]}
              value={value} disabled={saving} required onChange={event => setValue(event.target.value)} />
          </label>
          <label>Reason for correction
            <textarea required maxLength={1000} disabled={saving} value={reason}
              onChange={event => setReason(event.target.value)} />
          </label>
          <label>Reference measurement / calibration evidence
            <textarea required maxLength={1000} disabled={saving} value={evidence}
              onChange={event => setEvidence(event.target.value)} />
          </label>
          <button type="submit" disabled={saving || loading || loadFailed}>
            {saving ? 'Saving…' : 'Save documented correction'}
          </button>
        </form>
      )}
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      <h4>Manual correction history (latest 100)</h4>
      {!loading && !loadFailed && records.length === 0 && <p>No corrections recorded.</p>}
      <ul>
        {records.map(record => (
          <li key={record.id}>
            <strong>{FIELDS.find(spec => spec[0] === record.field)?.[1]}:</strong>
            {' '}{record.original_value} → {record.corrected_value} (proposed, not verified)
            <p>{record.reason} — Evidence: {record.evidence}</p>
            <p>By {record.recorded_by} · {new Date(record.created_at).toLocaleString()}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
