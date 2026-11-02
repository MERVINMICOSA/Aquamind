import {
  useEffect,
  useState,
} from 'react'

import {
  checkBackendConnection,
} from '../../services/backendHealthService'


type BackendConnectionStatus =
  | 'checking'
  | 'online'
  | 'offline'


const HEALTH_CHECK_INTERVAL_MS =
  30_000


function getStatusLabel(
  status: BackendConnectionStatus,
): string {
  switch (status) {
    case 'online':
      return 'Backend online'

    case 'offline':
      return 'Backend offline'

    case 'checking':
      return 'Checking backend'
  }
}


export function ConnectionStatus() {
  const [
    status,
    setStatus,
  ] = useState<BackendConnectionStatus>(
    'checking',
  )


  useEffect(() => {
    let active = true


    async function updateStatus():
      Promise<void> {
      const connected =
        await checkBackendConnection()

      if (!active) {
        return
      }

      setStatus(
        connected
          ? 'online'
          : 'offline',
      )
    }


    void updateStatus()

    const intervalId =
      window.setInterval(
        () => {
          void updateStatus()
        },
        HEALTH_CHECK_INTERVAL_MS,
      )


    return () => {
      active = false

      window.clearInterval(
        intervalId,
      )
    }
  }, [])


  return (
    <div
      className={[
        'connection-status',
        `connection-status--${status}`,
      ].join(' ')}
      role="status"
      aria-live="polite"
    >
      <span
        className="connection-status__indicator"
        aria-hidden="true"
      />

      <span>
        {getStatusLabel(
          status,
        )}
      </span>
    </div>
  )
}