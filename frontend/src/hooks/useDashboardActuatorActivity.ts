import {
  useEffect,
  useState,
} from 'react'

import {
  loadActuatorHistoryPage,
} from '../services/actuatorService'

import type {
  ActuatorEvent,
} from '../services/actuatorService'


type LoadStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'error'


interface DashboardActuatorActivity {
  events: ActuatorEvent[]
  status: LoadStatus
  errorMessage: string | null
}


export function useDashboardActuatorActivity(
  actuatorId: string | null,
): DashboardActuatorActivity {
  const [
    result,
    setResult,
  ] = useState<{
    actuatorId: string | null
    events: ActuatorEvent[]
    status: LoadStatus
    errorMessage: string | null
  }>({
    actuatorId: null,
    events: [],
    status: 'idle',
    errorMessage: null,
  })


  useEffect(() => {
    if (actuatorId === null) {
      return
    }

    let active = true

    loadActuatorHistoryPage(
      actuatorId,
      0,
    )
      .then(page => {
        if (!active) {
          return
        }

        setResult({
          actuatorId,
          events: page.events,
          status: 'ready',
          errorMessage: null,
        })
      })
      .catch(() => {
        if (!active) {
          return
        }

        setResult({
          actuatorId,
          events: [],
          status: 'error',
          errorMessage:
            'Unable to load persisted actuator activity.',
        })
      })

    return () => {
      active = false
    }
  }, [
    actuatorId,
  ])


  if (actuatorId === null) {
    return {
      events: [],
      status: 'idle',
      errorMessage: null,
    }
  }

  if (
    result.actuatorId !== actuatorId
  ) {
    return {
      events: [],
      status: 'loading',
      errorMessage: null,
    }
  }

  return {
    events: result.events,
    status: result.status,
    errorMessage: result.errorMessage,
  }
}