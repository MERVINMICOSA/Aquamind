import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  getEsp32CaptureSettings,
  updateEsp32CaptureSettings,
} from '../../services/esp32TelemetryService'
import type { Esp32CaptureMode, Esp32CaptureSettings as CaptureConfig } from '../../services/esp32TelemetryService'
import './Esp32CaptureSettings.css'

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

function formatInterval(minutes: number): string {
  return minutes % 60 === 0 && minutes >= 60
    ? `${minutes / 60} ${minutes === 60 ? 'hour' : 'hours'}`
    : `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`
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
        setClock(Date.now())
        if (first) {
          setMode(next.mode)
          setMinutes(String(next.interval_minutes))
          setChoice(PRESETS.includes(next.interval_minutes) ? String(next.interval_minutes) : 'custom')
          first = false
        }
        setStatus('ready')
      } catch {
        if (active && first) setStatus('error')
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
  const validInterval = minutes.trim().length > 0 && Number.isInteger(integerMinutes) &&
    integerMinutes >= 1 && integerMinutes <= 1440
  const savingMinutes = validInterval ? integerMinutes : (config?.interval_minutes ?? 5)
  const valid = mode === 'live' || validInterval
  const changed = config !== null && (mode !== config.mode ||
    (mode === 'timed' && savingMinutes !== config.interval_minutes))
  const remaining = clock > 0 && config?.next_save_at
    ? Math.max(0, Math.ceil((Date.parse(config.next_save_at) - clock) / 1000))
    : null

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canManage || !valid || !changed || saving) return
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const next = await updateEsp32CaptureSettings(systemId, mode, savingMinutes)
      setConfig(next)
      setMode(next.mode)
      setMinutes(String(next.interval_minutes))
      setChoice(PRESETS.includes(next.interval_minutes) ? String(next.interval_minutes) : 'custom')
      setClock(Date.now())
      setSuccess(true)
    } catch {
      setError('Unable to save ESP32 collection settings. Check your connection and administrator permissions.')
    } finally {
      setSaving(false)
    }
  }

  const recentlyReceived = config?.latest_received_at && clock > 0 &&
    Number.isFinite(Date.parse(config.latest_received_at)) &&
    clock - Date.parse(config.latest_received_at) < 45000

  return (
    <section className="surface-panel esp32-capture" aria-labelledby="esp32-capture-heading">
      <div className="esp32-capture__intro">
        <div className="esp32-capture__intro-row">
          <div>
            <p className="eyebrow">ESP32 USB Serial</p>
            <h2 id="esp32-capture-heading">ESP32 data collection</h2>
          </div>
          {config !== null && status === 'ready' && (
            <span className="esp32-capture__badge" data-mode={config.mode}>
              {config.mode === 'live' ? 'Live recording' : 'Timed recording'}
            </span>
          )}
        </div>
        <p className="page-description">
          Live readings remain available in either mode. Choose how often the latest
          valid ESP32 packets are added to Sensor History. This does not change
          how frequently the ESP32 firmware sends readings.
        </p>
      </div>

      {status === 'loading' && <p role="status">Loading data collection settings...</p>}
      {status === 'error' && <p role="alert" className="status-message status-message--error">
        Unable to load ESP32 data collection settings. Check the API connection and reload the page.
      </p>}

      {status === 'ready' && config && (
        <div className="esp32-capture__layout">
          <form className="esp32-capture__form" onSubmit={save}>
            <fieldset className="esp32-capture__fieldset" disabled={!canManage || saving}>
              <legend>History recording mode</legend>
              <div className="esp32-capture__modes">
                <label className="esp32-capture__mode" data-selected={mode === 'live'}>
                  <input type="radio" name="esp32-mode" value="live"
                    checked={mode === 'live'}
                    onChange={() => { setMode('live'); setSuccess(false) }} />
                  <span>
                    <strong>Live — save every valid packet</strong>
                    <small>Stores every distinct accepted reading. Uses more database space.</small>
                  </span>
                </label>
                <label className="esp32-capture__mode" data-selected={mode === 'timed'}>
                  <input type="radio" name="esp32-mode" value="timed"
                    checked={mode === 'timed'}
                    onChange={() => { setMode('timed'); setSuccess(false) }} />
                  <span>
                    <strong>Timed — save at selected intervals</strong>
                    <small>Displays live measurements but saves one fresh packet per interval.</small>
                  </span>
                </label>
              </div>
            </fieldset>

            {mode === 'timed' && (
              <div className="esp32-capture__interval">
                <label htmlFor="esp32-save-interval">Saving interval</label>
                <select id="esp32-save-interval" aria-label="Saving interval"
                  disabled={!canManage || saving}
                  value={choice}
                  onChange={event => {
                    const next = event.target.value
                    setChoice(next)
                    if (next !== 'custom') setMinutes(next)
                    setSuccess(false)
                  }}>
                  {PRESETS.map(value => (
                    <option key={value} value={value}>{formatInterval(value)}</option>
                  ))}
                  <option value="custom">Custom interval</option>
                </select>
                {choice === 'custom' && (
                  <label className="esp32-capture__custom">
                    Custom interval (minutes, 1–1440)
                    <input type="number" min="1" max="1440" step="1"
                      disabled={!canManage || saving}
                      value={minutes}
                      onChange={event => { setMinutes(event.target.value); setSuccess(false) }} />
                  </label>
                )}
                {!validInterval && <p role="alert" className="esp32-capture__validation">
                  Enter a whole number between 1 and 1440.
                </p>}
              </div>
            )}

            <p className="esp32-capture__note">
              Timed mode skips missing intervals and packets older than 45 seconds
              at the save boundary. Repeated packets are not archived twice.
            </p>

            <div className="esp32-capture__actions">
              {canManage ? (
                <button type="submit" className="primary-button"
                  disabled={saving || !valid || !changed}>
                  {saving ? 'Saving...' : 'Save ESP32 collection settings'}
                </button>
              ) : (
                <p className="esp32-capture__readonly">Administrator access is required to change collection settings.</p>
              )}
              {error && <p role="alert" className="status-message status-message--error">{error}</p>}
              {success && <p role="status" className="esp32-capture__saved">ESP32 collection settings saved.</p>}
            </div>
          </form>

          <aside className="esp32-capture__status" aria-label="Collection status">
            <div className="esp32-capture__status-head">
              <h3>Collection status</h3>
              <span className="esp32-capture__device-state"
                data-connected={Boolean(recentlyReceived)}>
                <span aria-hidden="true" />
                {recentlyReceived ? 'Receiving data' : 'No recent packet'}
              </span>
            </div>
            <dl className="esp32-capture__status-grid">
              <div><dt>Device</dt><dd>{config.device_id ?? 'Awaiting an ESP32 packet'}</dd></div>
              <div><dt>Active mode</dt><dd>{config.mode === 'live'
                ? 'Live · every packet'
                : `Timed · ${formatInterval(config.interval_minutes)}`}</dd></div>
              <div><dt>Last received</dt><dd>{formatTime(config.latest_received_at)}</dd></div>
              <div><dt>Last saved to history</dt><dd>{formatTime(config.last_saved_at)}</dd></div>
              {config.mode === 'timed' && (
                <>
                  <div><dt>Next scheduled save</dt><dd>{formatTime(config.next_save_at)}</dd></div>
                  <div className="esp32-capture__countdown">
                    <dt>Time remaining</dt>
                    <dd role="timer">{remaining === null ? 'Not scheduled'
                      : remaining === 0 ? 'Due · awaiting server'
                      : `${Math.floor(remaining / 60)}m ${String(remaining % 60).padStart(2, '0')}s`}</dd>
                  </div>
                </>
              )}
            </dl>
            <p className="esp32-capture__hint">
              The countdown shows the server's scheduled save time, not a measurement
              timestamp. If the ESP32 is offline, an interval can be skipped.
            </p>
          </aside>
        </div>
      )}
    </section>
  )
}
