import {
  useEffect,
  useState,
} from 'react'

import {
  loadSensorHistoryPage,
} from '../services/sensorService'

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

    const activeSensorId =
      sensorId

    let active =
      true


    async function loadTrend():
      Promise<void> {
      try {
        setStatus(
          'loading',
        )

        setErrorMessage(
          null,
        )

        const result =
          await loadSensorHistoryPage(
            activeSensorId,
            0,
          )

        if (!active) {
          return
        }

        setReadings(
          result.readings,
        )

        setStatus(
          'ready',
        )
      } catch {
        if (!active) {
          return
        }

        setReadings(
          [],
        )

        setErrorMessage(
          'Unable to load sensor reading history.',
        )

        setStatus(
          'error',
        )
      }
    }


    void loadTrend()


    return () => {
      active = false
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
