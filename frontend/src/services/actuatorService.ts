import type {
  DashboardActuator,
} from '../types/dashboard'

import {
  apiRequest,
} from './apiClient'

export interface ActuatorEvent {
  id: string
  actuator_id: string
  command_type: string
  requested_value: number | null
  actual_value: number | null
  started_at: string
  completed_at: string | null
  duration_ms: number | null
  trigger_source: string
  status: string
  fault_code: string | null
  error_message: string | null
  created_at: string
}

export const ACTUATOR_HISTORY_PAGE_SIZE = 50

export interface ActuatorHistoryPage {
  events: ActuatorEvent[]
  hasNext: boolean
  hasPrevious: boolean
  offset: number
}

export async function getActuator(actuatorId: string): Promise<DashboardActuator> {
  return apiRequest<DashboardActuator>(`actuators/${encodeURIComponent(actuatorId)}`)
}

export async function loadActuatorHistoryPage(
  actuatorId: string,
  offset: number,
): Promise<ActuatorHistoryPage> {
  const normalizedOffset = Math.max(0, Math.trunc(offset))
  const result = await apiRequest<ActuatorEvent[]>(
    `actuator-events/history?actuator_id=${encodeURIComponent(actuatorId)}` +
    `&limit=${ACTUATOR_HISTORY_PAGE_SIZE + 1}&offset=${normalizedOffset}`,
  )
  return {
    events: result.slice(0, ACTUATOR_HISTORY_PAGE_SIZE),
    hasNext: result.length > ACTUATOR_HISTORY_PAGE_SIZE,
    hasPrevious: normalizedOffset > 0,
    offset: normalizedOffset,
  }
}


export interface SystemActuatorOverview {
  actuators:
    DashboardActuator[]
}


export async function loadSystemActuatorOverview(
  systemId: string,
): Promise<SystemActuatorOverview> {
  const encodedSystemId =
    encodeURIComponent(
      systemId,
    )

  const actuators =
    await apiRequest<
      DashboardActuator[]
    >(
      `actuators?system_id=${encodedSystemId}`,
    )

  return {
    actuators,
  }
}
