import type {
  Tank,
} from '../types/tank'

import {
  apiRequest,
} from './apiClient'


export async function listSystemTanks(
  systemId: string,
): Promise<Tank[]> {
  const encodedSystemId =
    encodeURIComponent(
      systemId,
    )

  return apiRequest<Tank[]>(
    `tanks?system_id=${encodedSystemId}`,
  )
}