import {
  useEffect,
  useState,
} from 'react'

import {
  loadSensorHistoryPage,
} from '../services/sensorService'
import { listEsp32Telemetry } from '../services/esp32TelemetryService'
import { archivedTrendReadings, parseArchiveSensorId } from '../utils/esp32DashboardReadings'

import type {
  DashboardSensorReading,
} from '../types/dashboard'


type LoadStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'error'


export function useDashboardSensorTrend(
  sensorId: string | null,
) {
  const [
    readings,
    setReadings,
  ] = useState<DashboardSensorReading[]>(
    [],
  )

  const [
    status,
    setStatus,
  ] = useState<LoadStatus>(
    'idle',
  )

  const [
    errorMessage,
    setErrorMessage,
  ] = useState<string | null>(
    null,
  )


  useEffect(() => {
    if (sensorId === null) {
      return
    }

    const activeSensorId = sensorId
    const archived = parseArchiveSensorId(activeSensorId)
    let active = true
    let busy = false
    let loaded = false

    async function loadTrend(): Promise<void> {
      if (busy) return
      busy = true
      if (!loaded) setStatus('loading')

      try {
        const next = archived
          ? archivedTrendReadings(
              await listEsp32Telemetry(archived.systemId, 50),
              activeSensorId,
            )
          : (await loadSensorHistoryPage(activeSensorId, 0)).readings

        if (!active) return
        setReadings(next)
        setStatus('ready')
        setErrorMessage(null)
        loaded = true
      } catch {
        if (!active) return
        if (!loaded) {
          setReadings([])
          setStatus('error')
        }
        setErrorMessage('Unable to refresh sensor reading history.')
      } finally {
        busy = false
      }
    }

    setReadings([])
    void loadTrend()
    const timer = window.setInterval(() => { void loadTrend() }, 10000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [
    sensorId,
  ])


  return {
    readings,
    status:
      sensorId === null
        ? 'idle' as const
        : status,
    errorMessage,
  }
}
