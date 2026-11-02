import type {
  AquaponicsSystem,
  DashboardActuator,
  DashboardAlert,
  DashboardSensor,
  DashboardSensorReading,
  SystemDashboardOverview,
} from '../types/dashboard'

import {
  apiRequest,
} from './apiClient'


export async function listSystems():
  Promise<AquaponicsSystem[]> {
  return apiRequest<AquaponicsSystem[]>(
    'systems',
  )
}


export async function loadSystemDashboardOverview(
  systemId: string,
): Promise<SystemDashboardOverview> {
  const encodedSystemId =
    encodeURIComponent(
      systemId,
    )

  const [
    sensors,
    actuators,
    alerts,
    latestReadings,
  ] = await Promise.all([
    apiRequest<DashboardSensor[]>(
      `sensors?system_id=${encodedSystemId}`,
    ),

    apiRequest<DashboardActuator[]>(
      `actuators?system_id=${encodedSystemId}`,
    ),

    apiRequest<DashboardAlert[]>(
      `alerts?system_id=${encodedSystemId}`,
    ),

    apiRequest<DashboardSensorReading[]>(
      `sensor-readings/latest?system_id=${encodedSystemId}`,
    ),
  ])

  return {
    sensors,
    actuators,
    alerts,
    latestReadings,
  }
}