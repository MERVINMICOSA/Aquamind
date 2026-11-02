import { useEffect, useState } from 'react'
import {
  ACTUATOR_HISTORY_PAGE_SIZE,
  getActuator,
  loadActuatorHistoryPage,
} from '../services/actuatorService'
import type { ActuatorHistoryPage } from '../services/actuatorService'
import type { DashboardActuator } from '../types/dashboard'

type LoadStatus = 'loading' | 'ready' | 'error'

export function useActuatorDetail(actuatorId: string | undefined) {
  const [page, setPage] = useState({ actuatorId, offset: 0 })
  const offset = page.actuatorId === actuatorId ? page.offset : 0
  const [detail, setDetail] = useState<{
    actuatorId: string
    actuator: DashboardActuator | null
    status: LoadStatus
  } | null>(null)
  const [history, setHistory] = useState<{
    actuatorId: string
    offset: number
    data: ActuatorHistoryPage | null
    status: LoadStatus
  } | null>(null)

  useEffect(() => {
    if (actuatorId === undefined) return
    let active = true
    async function load() {
      try {
        const actuator = await getActuator(actuatorId!)
        if (active) setDetail({ actuatorId: actuatorId!, actuator, status: 'ready' })
      } catch {
        if (active) setDetail({ actuatorId: actuatorId!, actuator: null, status: 'error' })
      }
    }
    void load()
    return () => { active = false }
  }, [actuatorId])

  useEffect(() => {
    if (actuatorId === undefined) return
    let active = true
    async function load() {
      setHistory({ actuatorId: actuatorId!, offset, data: null, status: 'loading' })
      try {
        const data = await loadActuatorHistoryPage(actuatorId!, offset)
        if (active) setHistory({ actuatorId: actuatorId!, offset, data, status: 'ready' })
      } catch {
        if (active) setHistory({ actuatorId: actuatorId!, offset, data: null, status: 'error' })
      }
    }
    void load()
    return () => { active = false }
  }, [actuatorId, offset])

  // Never expose data belonging to a previous route or page.
  const currentDetail = detail?.actuatorId === actuatorId ? detail : null
  const currentHistory = history?.actuatorId === actuatorId && history?.offset === offset
    ? history : null
  const historyStatus = currentHistory?.status ?? 'loading'
  const hasNext = currentHistory?.data?.hasNext ?? false

  return {
    actuator: currentDetail?.actuator ?? null,
    actuatorStatus: currentDetail?.status ?? 'loading',
    events: currentHistory?.data?.events ?? [],
    historyStatus,
    hasNext,
    hasPrevious: offset > 0,
    pageNumber: Math.floor(offset / ACTUATOR_HISTORY_PAGE_SIZE) + 1,
    nextPage() {
      if (historyStatus === 'ready' && hasNext) {
        setPage({ actuatorId, offset: offset + ACTUATOR_HISTORY_PAGE_SIZE })
      }
    },
    previousPage() {
      if (historyStatus !== 'loading' && offset > 0) {
        setPage({ actuatorId, offset: Math.max(0, offset - ACTUATOR_HISTORY_PAGE_SIZE) })
      }
    },
  }
}
