import { useEffect, useState } from 'react'
import { listSystems } from '../services/dashboardService'
import { ALERT_HISTORY_PAGE_SIZE, loadAlertHistoryPage, updateAlertLifecycle } from '../services/alertService'
import type { AlertHistoryPage } from '../services/alertService'
import type { AquaponicsSystem, DashboardAlert } from '../types/dashboard'

type LoadStatus = 'loading' | 'ready' | 'error'

export function useAlertsOverview() {
  const [systems, setSystems] = useState<AquaponicsSystem[]>([])
  const [systemsStatus, setSystemsStatus] = useState<LoadStatus>('loading')
  const [selection, setSelection] = useState({ systemId: null as string | null, offset: 0, revision: 0 })
  const [history, setHistory] = useState<{
    systemId: string
    offset: number
    revision: number
    status: LoadStatus
    data: AlertHistoryPage | null
  } | null>(null)

  const [mutation, setMutation] = useState<{
    systemId: string
    status: 'saving' | 'error'
    error: string | null
  } | null>(null)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const result = await listSystems()
        if (!active) return
        const ordered = [...result].sort((left, right) => left.name.localeCompare(right.name))
        setSystems(ordered)
        setSelection({ systemId: ordered[0]?.id ?? null, offset: 0, revision: 0 })
        setSystemsStatus('ready')
      } catch {
        if (active) setSystemsStatus('error')
      }
    }
    void load()
    return () => { active = false }
  }, [])

  useEffect(() => {
    const { systemId, offset, revision } = selection
    if (systemId === null) return
    let active = true
    async function load() {
      try {
        const data = await loadAlertHistoryPage(systemId!, offset)
        if (active) setHistory({ systemId: systemId!, offset, revision, status: 'ready', data })
      } catch {
        if (active) setHistory({ systemId: systemId!, offset, revision, status: 'error', data: null })
      }
    }
    void load()
    return () => { active = false }
  }, [selection])

  // Include the selection revision so returning to a system/page cannot reveal old data.
  const currentHistory = history?.systemId === selection.systemId &&
    history?.offset === selection.offset && history?.revision === selection.revision ? history : null
  const historyStatus = currentHistory?.status ?? 'loading'
  const hasNext = currentHistory?.data?.hasNext ?? false

  const mutationStatus = mutation?.systemId === selection.systemId
    ? mutation.status : 'idle'
  const mutationError = mutation?.systemId === selection.systemId
    ? mutation.error : null

  async function changeAlertStatus(
    alert: DashboardAlert,
    status: 'acknowledged' | 'resolved',
    reason?: string,
  ): Promise<boolean> {
    const systemId = selection.systemId
    if (systemId === null || alert.system_id !== systemId || mutationStatus === 'saving') {
      return false
    }
    setMutation({ systemId, status: 'saving', error: null })
    try {
      await updateAlertLifecycle(alert.id, status, reason)
      // Refresh only the current selected page, never a different system's data.
      setSelection(current => current.systemId === systemId
        ? { ...current, revision: current.revision + 1 }
        : current)
      setMutation(null)
      return true
    } catch {
      setMutation({
        systemId,
        status: 'error',
        error: status === 'acknowledged'
          ? 'Unable to acknowledge this alert.'
          : 'Unable to resolve this alert.',
      })
      return false
    }
  }

  return {
    mutationStatus,
    mutationError,
    acknowledgeAlert: (alert: DashboardAlert) =>
      changeAlertStatus(alert, 'acknowledged'),
    resolveAlert: (alert: DashboardAlert, reason: string) =>
      changeAlertStatus(alert, 'resolved', reason),
    systems,
    systemsStatus,
    selectedSystemId: selection.systemId,
    selectedSystem: systems.find(system => system.id === selection.systemId) ?? null,
    alerts: currentHistory?.data?.alerts ?? [],
    historyStatus,
    hasNext,
    hasPrevious: selection.offset > 0,
    pageNumber: Math.floor(selection.offset / ALERT_HISTORY_PAGE_SIZE) + 1,
    selectSystem(systemId: string) {
      if (!systems.some(system => system.id === systemId)) return
      setSelection(current => current.systemId === systemId ? current : {
        systemId, offset: 0, revision: current.revision + 1,
      })
    },
    nextPage() {
      if (historyStatus !== 'ready' || !hasNext) return
      setSelection(current => ({ ...current, offset: current.offset + ALERT_HISTORY_PAGE_SIZE, revision: current.revision + 1 }))
    },
    previousPage() {
      if (historyStatus === 'loading' || selection.offset === 0) return
      setSelection(current => ({ ...current, offset: Math.max(0, current.offset - ALERT_HISTORY_PAGE_SIZE), revision: current.revision + 1 }))
    },
  }
}
