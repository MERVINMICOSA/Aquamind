import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  getEsp32CaptureSettings,
  updateEsp32CaptureSettings,
} from '../../services/esp32TelemetryService'
import type { Esp32CaptureMode, Esp32CaptureSettings as CaptureConfig } from '../../services/esp32TelemetryService'

interface Props {
  systemId: string
  canManage: boolean
}

const PRESETS = [1, 5, 10, 15, 30, 60, 120, 360, 720, 1440]

function formatTime(value: string | null | undefined): string {
  if (!value) return 'Not recorded'
  const timestamp = new Date(value)
  return Number.isNaN(timestamp.getTime()) ? 'Unknown time' : timestamp.toLocaleString()
}

/** Dedicated validated controls; generic key/value settings do not operate devices. */
export function Esp32CaptureSettings({ systemId, canManage }: Props) {
  const [config, setConfig] = useState<CaptureConfig | null>(null)
  const [mode, setMode] = useState<Esp32CaptureMode>('live')
  const [minutes, setMinutes] = useState('5')
  const [choice, setChoice] = useState('5')
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [clock, setClock] = useState(0)

  useEffect(() => {
    let active = true
    let first = true
    const refresh = async () => {
      try {
        const next = await getEsp32CaptureSettings(systemId)
        if (!active) return
        setConfig(next)
        if (first) {
          setMode(next.mode)
          setMinutes(String(next.interval_minutes))
          setChoice(PRESETS.includes(next.interval_minutes) ? String(next.interval_minutes) : 'custom')
        }
        setStatus('ready')
      } catch {
        if (active && first) setStatus('error')
      } finally {
        first = false
      }
    }
    void refresh()
    const refreshTimer = window.setInterval(() => { void refresh() }, 10000)
    const clockTimer = window.setInterval(() => setClock(Date.now()), 1000)
    return () => {
      active = false
      window.clearInterval(refreshTimer)
      window.clearInterval(clockTimer)
    }
  }, [systemId])

  const integerMinutes = Number(minutes)
  const valid = Number.isInteger(integerMinutes) && integerMinutes >= 1 && integerMinutes <= 1440
  const remaining = config?.next_save_at
    ? Math.max(0, Math.ceil((Date.parse(config.next_save_at) - clock) / 1000))
    : null

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canManage || !valid || saving) return
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const next = await updateEsp32CaptureSettings(systemId, mode, integerMinutes)
      setConfig(next)
      setMode(next.mode)
      setMinutes(String(next.interval_minutes))
      setChoice(PRESETS.includes(next.interval_minutes) ? String(next.interval_minutes) : 'custom')
      setSuccess(true)
    } catch {
      setError('Unable to save ESP32 collection settings. Check your connection and administrator permissions.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="surface-panel" aria-labelledby="esp32-capture-heading">
      <div>
        <p className="eyebrow">ESP32 USB Serial</p>
        <h2 id="esp32-capture-heading">ESP32 data collection</h2>
        <p className="page-description">
          Current sensor readings update whenever the ESP32 sends a valid packet.
          Choose how many of those packets should be stored in historical data.
          This setting does not change ESP32 firmware transmission frequency.
        </p>
      </div>
      {status === 'loading' && <p role="status">Loading data collection settings...</p>}
      {status === 'error' && <p role="alert">Unable to load ESP32 data collection settings.</p>}
      {status === 'ready' && config && (
        <>
          <form className="stack-form" onSubmit={save}>
            <fieldset disabled={!canManage || saving}>
              <legend>History recording mode</legend>
              <label className="control-field">
                <span>
                  <input type="radio" name="esp32-mode" value="live"
                    checked={mode === 'live'}
                    onChange={() => { setMode('live'); setSuccess(false) }} />
                  {' '}Live — save every valid packet
                </span>
              </label>
              <label className="control-field">
                <span>
                  <input type="radio" name="esp32-mode" value="timed"
                    checked={mode === 'timed'}
                    onChange={() => { setMode('timed'); setSuccess(false) }} />
                  {' '}Timed — save the final fresh packet before each timer boundary
                </span>
              </label>
              {mode === 'timed' && (
                <>
                  <label className="control-field">
                    <span>Saving interval</span>
                    <select aria-label="Saving interval" value={choice}
                      onChange={event => {
                        const next = event.target.value
                        setChoice(next)
                        if (next !== 'custom') setMinutes(next)
                        setSuccess(false)
                      }}>
                      {PRESETS.map(value => (
                        <option key={value} value={value}>
                          {value >= 60 && value % 60 === 0 ? `${value / 60} hour(s)` : `${value} minute(s)`}
                        </option>
                      ))}
                      <option value="custom">Custom interval</option>
                    </select>
                  </label>
                  {choice === 'custom' && (
                    <label className="control-field">
                      <span>Custom interval (minutes, 1–1440)</span>
                      <input type="number" min="1" max="1440" step="1" value={minutes}
                        onChange={event => { setMinutes(event.target.value); setSuccess(false) }} />
                    </label>
                  )}
                  {!valid && <p role="alert">Enter a whole number between 1 and 1440.</p>}
                </>
              )}
            </fieldset>
            <p className="data-note">
              Timed mode skips missed intervals and packets more than 45 seconds old at
              the save boundary. Repeated packets never generate duplicate history.
              Live mode can increase database storage rapidly.
            </p>
            {canManage && (
              <button type="submit" className="primary-button" disabled={saving || !valid}>
                {saving ? 'Saving...' : 'Save ESP32 collection settings'}
              </button>
            )}
            {error && <p role="alert" className="status-message status-message--error">{error}</p>}
            {success && <p role="status">ESP32 collection settings saved.</p>}
          </form>
          <div>
            <h3>Collection status</h3>
            <p>Device: {config.device_id ?? 'Awaiting an ESP32 packet'}</p>
            <p>Active mode: {config.mode === 'live' ? 'Live — all packets' : `Timed — every ${config.interval_minutes} minute(s)`}</p>
            <p>Last received: {formatTime(config.latest_received_at)}</p>
            <p>Last saved to history: {formatTime(config.last_saved_at)}</p>
            {config.mode === 'timed' && (
              <>
                <p>Next scheduled save: {formatTime(config.next_save_at)}</p>
                <p role="timer">
                  Countdown: {remaining === null ? 'Not scheduled' : remaining === 0 ? 'Due — awaiting server' : `${Math.floor(remaining / 60)}m ${String(remaining % 60).padStart(2, '0')}s`}
                </p>
              </>
            )}
          </div>
        </>
      )}
    </section>
  )
}
