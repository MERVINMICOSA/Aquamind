import type { DashboardAlert } from '../types/dashboard'
import { apiRequest } from './apiClient'

export const ALERT_HISTORY_PAGE_SIZE = 50

export interface AlertHistoryPage {
  alerts: DashboardAlert[]
  hasNext: boolean
  hasPrevious: boolean
  offset: number
}

export async function loadAlertHistoryPage(
  systemId: string,
  offset: number,
): Promise<AlertHistoryPage> {
  const normalizedOffset = Math.max(0, Math.trunc(offset))
  const alerts = await apiRequest<DashboardAlert[]>(
    `alerts/history?system_id=${encodeURIComponent(systemId)}` +
    `&limit=${ALERT_HISTORY_PAGE_SIZE + 1}&offset=${normalizedOffset}`,
  )
  return {
    alerts: alerts.slice(0, ALERT_HISTORY_PAGE_SIZE),
    hasNext: alerts.length > ALERT_HISTORY_PAGE_SIZE,
    hasPrevious: normalizedOffset > 0,
    offset: normalizedOffset,
  }
}


/**
 * Alert status is a server-owned lifecycle. The backend supplies the
 * authenticated acknowledger and timestamps; the browser supplies only
 * the requested transition and a reason for resolution.
 */
export async function updateAlertLifecycle(
  alertId: string,
  status: 'acknowledged' | 'resolved',
  resolutionReason?: string,
): Promise<DashboardAlert> {
  return apiRequest<DashboardAlert>(
    `alerts/${encodeURIComponent(alertId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        status,
        ...(status === 'resolved' ? { resolution_reason: resolutionReason } : {}),
      }),
    },
  )
}
