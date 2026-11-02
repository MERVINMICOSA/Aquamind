import type {
  DashboardSensor,
  DashboardSensorReading,
} from '../types/dashboard'

import {
  apiRequest,
} from './apiClient'


export const SENSOR_HISTORY_PAGE_SIZE =
  50


export interface SystemSensorOverview {
  sensors: DashboardSensor[]
  latestReadings:
    DashboardSensorReading[]
}


export interface SensorHistoryPage {
  readings:
    DashboardSensorReading[]

  hasNext:
    boolean

  hasPrevious:
    boolean

  offset:
    number
}


// ============================================================
// SYSTEM SENSOR OVERVIEW
// ============================================================


export async function loadSystemSensorOverview(
  systemId: string,
): Promise<SystemSensorOverview> {
  const encodedSystemId =
    encodeURIComponent(
      systemId,
    )

  const [
    sensors,
    latestReadings,
  ] = await Promise.all([
    apiRequest<DashboardSensor[]>(
      `sensors?system_id=${encodedSystemId}`,
    ),

    apiRequest<DashboardSensorReading[]>(
      `sensor-readings/latest?system_id=${encodedSystemId}`,
    ),
  ])

  return {
    sensors,
    latestReadings,
  }
}


// ============================================================
// SENSOR DETAIL
// ============================================================


export async function getSensor(
  sensorId: string,
): Promise<DashboardSensor> {
  const encodedSensorId =
    encodeURIComponent(
      sensorId,
    )

  return apiRequest<DashboardSensor>(
    `sensors/${encodedSensorId}`,
  )
}


// ============================================================
// SENSOR HISTORY
// ============================================================


export async function loadSensorHistoryPage(
  sensorId: string,
  offset: number,
): Promise<SensorHistoryPage> {
  const encodedSensorId =
    encodeURIComponent(
      sensorId,
    )

  const normalizedOffset =
    Math.max(
      0,
      Math.trunc(
        offset,
      ),
    )

  /*
   * Fetch one extra row.
   *
   * We display 50 readings and use row 51 only to
   * determine whether another real page exists.
   */
  const requestLimit =
    SENSOR_HISTORY_PAGE_SIZE +
    1

  const result =
    await apiRequest<
      DashboardSensorReading[]
    >(
      `sensor-readings/history?sensor_id=${encodedSensorId}` +
        `&limit=${requestLimit}` +
        `&offset=${normalizedOffset}`,
    )

  return {
    readings:
      result.slice(
        0,
        SENSOR_HISTORY_PAGE_SIZE,
      ),

    hasNext:
      result.length >
      SENSOR_HISTORY_PAGE_SIZE,

    hasPrevious:
      normalizedOffset > 0,

    offset:
      normalizedOffset,
  }
}