import type {
  RefillEvent,
  Reservoir,
} from '../types/refill'

import {
  apiRequest,
} from './apiClient'


export const REFILL_HISTORY_PAGE_SIZE =
  50


export interface RefillHistoryPage {
  events: RefillEvent[]

  hasNext: boolean
  hasPrevious: boolean

  offset: number
}


export async function listSystemReservoirs(
  systemId: string,
): Promise<Reservoir[]> {
  const encodedSystemId =
    encodeURIComponent(
      systemId,
    )

  return apiRequest<Reservoir[]>(
    `reservoirs?system_id=${encodedSystemId}`,
  )
}


export async function loadRefillHistoryPage(
  reservoirId: string,
  offset: number,
): Promise<RefillHistoryPage> {
  const normalizedOffset =
    Math.max(
      0,
      Math.trunc(
        offset,
      ),
    )

  const encodedReservoirId =
    encodeURIComponent(
      reservoirId,
    )

  const rows =
    await apiRequest<RefillEvent[]>(
      (
        'refill-events/history'
        + `?reservoir_id=${encodedReservoirId}`
        + `&limit=${REFILL_HISTORY_PAGE_SIZE + 1}`
        + `&offset=${normalizedOffset}`
      ),
    )

  return {
    events:
      rows.slice(
        0,
        REFILL_HISTORY_PAGE_SIZE,
      ),

    hasNext:
      rows.length >
      REFILL_HISTORY_PAGE_SIZE,

    hasPrevious:
      normalizedOffset >
      0,

    offset:
      normalizedOffset,
  }
}