import { useEffect, useState } from 'react'
import { listEsp32Telemetry } from '../../services/esp32TelemetryService'
import type { Esp32SensorPacket, Esp32Telemetry } from '../../types/esp32Telemetry'
import './Esp32TelemetryPanel.css'

interface Props {
  systemId: string
}

function numeric(value: number | null, suffix = '', digits = 2): string {
  return value === null ? 'No reading' : `${value.toFixed(digits)}${suffix}`
}

function timestamp(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleString()
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

/**
 * Standalone, read-only view. It does not register values as calibrated
 * sensor readings or send any commands to pumps/actuators.
 */
export function Esp32TelemetryPanel({ systemId }: Props) {
  const [packets, setPackets] = useState<Esp32Telemetry[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  useEffect(() => {
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
    const timer = window.setInterval(() => void refresh(), 10000)

    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [systemId])

  const latest = packets[0] ?? null
  const packet = latest?.packet

  return (
    <section className="esp32-telemetry" aria-label="ESP32 device telemetry">
      <div className="esp32-telemetry__header">
        <div>
          <p className="eyebrow">ESP32 device telemetry</p>
          <h2>ESP32 sensor readings</h2>
        </div>
        <span>Saved packet history · Refreshes every 10 seconds</span>
      </div>

      {status === 'loading' && (
        <p role="status">Loading ESP32 sensor packets...</p>
      )}
      {status === 'error' && (
        <p role="alert">Cannot refresh ESP32 data. Previously saved values may be stale.</p>
      )}
      {status === 'ready' && latest === null && (
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

          <h3>Recent packets</h3>
          <div className="esp32-telemetry__history">
            <table>
              <thead>
                <tr><th>Received</th><th>Device</th><th>Sequence</th><th>Water °C</th><th>pH status</th><th>TDS status</th></tr>
              </thead>
              <tbody>
                {packets.map((item) => (
                  <tr key={item.id}>
                    <td>{timestamp(item.received_at)}</td>
                    <td>{item.packet.device_id}</td>
                    <td>{item.packet.sequence}</td>
                    <td>{numeric(item.packet.water_temp_c, '', 2)}</td>
                    <td>{item.packet.ph_calibrated ? 'Calibrated' : 'Unverified'}</td>
                    <td>{item.packet.tds_calibrated ? 'Calibrated' : 'Unverified'}</td>
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
