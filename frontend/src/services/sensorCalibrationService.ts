import { apiRequest } from './apiClient'

export type SensorCalibrationStatus =
  | 'pending'
  | 'verified'
  | 'rejected'
  | 'expired'

export interface SensorCalibrationRecord {
  id: string
  sensor_id: string
  offset: number
  factor: number
  calibration_data: Record<string, unknown> | null
  performed_at: string
  verified_by_user_id: string | null
  status: SensorCalibrationStatus
  notes: string | null
  created_at: string
}

/**
 * These are stored calibration audit records, NOT instructions to
 * recalibrate the ESP32. Backend returns records newest first.
 */
export async function listSensorCalibrationRecords(
  sensorId: string,
): Promise<SensorCalibrationRecord[]> {
  return apiRequest<SensorCalibrationRecord[]>(
    `sensor-calibrations?sensor_id=${encodeURIComponent(sensorId)}`,
  )
}
