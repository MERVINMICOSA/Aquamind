import { useEffect, useState } from 'react'
import {
  listSensorCalibrationRecords,
} from '../../services/sensorCalibrationService'
import type {
  SensorCalibrationRecord,
} from '../../services/sensorCalibrationService'

interface Props {
  sensorId: string
  sensorType: string
  calibrationStatus: string
}

type LoadStatus = 'loading' | 'ready' | 'error'

function formatTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export function SensorCalibrationPanel({
  sensorId,
  sensorType,
  calibrationStatus,
}: Props) {
  const [result, setResult] = useState<{
    sensorId: string
    status: LoadStatus
    calibrations: SensorCalibrationRecord[]
  } | null>(null)

  useEffect(() => {
    let active = true
    void listSensorCalibrationRecords(sensorId)
      .then((calibrations) => {
        if (active) {
          setResult({
            sensorId,
            status: 'ready',
            calibrations: calibrations.filter(
              (calibration) => calibration.sensor_id === sensorId,
            ),
          })
        }
      })
      .catch(() => {
        if (active) {
          setResult({ sensorId, status: 'error', calibrations: [] })
        }
      })

    return () => { active = false }
  }, [sensorId])

  const current = result?.sensorId === sensorId ? result : null
  const status = current?.status ?? 'loading'
  const calibrations = current?.calibrations ?? []
  const isCalibrationDependent = sensorType === 'ph' || sensorType === 'tds'
  const latest = calibrations[0] ?? null

  return (
    <section className="sensor-detail-panel" aria-labelledby="sensor-calibration-heading">
      <div className="sensor-detail-panel__heading">
        <div>
          <p className="eyebrow">Calibration</p>
          <h2 id="sensor-calibration-heading">Calibration records</h2>
        </div>
      </div>

      <p>
        Registered sensor status: <strong>{calibrationStatus.replaceAll('_', ' ')}</strong>.
        Calibration records are stored evidence only: saving a record does not
        adjust the ESP32 probe firmware or turn raw voltages into verified readings.
      </p>

      {isCalibrationDependent && calibrationStatus !== 'verified' && (
        <p role="status" className="status-message">
          This {sensorType === 'ph' ? 'pH' : 'TDS'} sensor is not marked as verified.
          Its readings must not be used for calibrated water-quality alerts.
        </p>
      )}

      {sensorType === 'ph' && (
        <p>
          Check the pH probe against known buffer solutions, record the measured
          reference points and temperature, and verify the resulting firmware
          calibration before approving it. Suitable pH buffers may include 4.01,
          6.86, and 9.18 at their specified reference temperature.
        </p>
      )}

      {sensorType === 'tds' && (
        <p>
          Use a known TDS or conductivity reference solution and temperature
          compensation appropriate to the probe. Unverified ppm estimates are
          diagnostic values, not calibrated TDS readings.
        </p>
      )}

      {status === 'loading' && (
        <p role="status">Loading saved calibration records...</p>
      )}
      {status === 'error' && (
        <p role="alert" className="status-message status-message--error">
          Unable to load calibration records. The sensor status above is
          configuration metadata, not independent proof of calibration.
        </p>
      )}
      {status === 'ready' && calibrations.length === 0 && (
        <p>No calibration records were returned for this sensor.</p>
      )}
      {status === 'ready' && latest !== null && (
        <>
          {calibrationStatus === 'verified' && latest.status !== 'verified' && (
            <p role="alert" className="status-message status-message--error">
              The registered sensor is marked verified, but the newest
              calibration record is {latest.status}. Review the mismatch.
            </p>
          )}
          <p>
            Showing {Math.min(calibrations.length, 5)} most recent of
            {' '}{calibrations.length} saved calibration records.
          </p>
          <div className="sensor-history-table-wrap">
            <table className="sensor-history-table" aria-label="Sensor calibration history">
              <thead>
                <tr>
                  <th>Performed</th>
                  <th>Status</th>
                  <th>Offset</th>
                  <th>Factor</th>
                  <th>Verified by</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {calibrations.slice(0, 5).map((calibration) => (
                  <tr key={calibration.id}>
                    <td>{formatTime(calibration.performed_at)}</td>
                    <td>{calibration.status}</td>
                    <td>{calibration.offset}</td>
                    <td>{calibration.factor}</td>
                    <td>{calibration.verified_by_user_id ?? 'Not recorded'}</td>
                    <td>{calibration.notes ?? 'Not recorded'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <p>
        ESP32 USB packets are archived separately from registered sensor readings
        and calibration records. This panel cannot confirm a physical probe's
        calibration without actual reference measurements.
      </p>
    </section>
  )
}
