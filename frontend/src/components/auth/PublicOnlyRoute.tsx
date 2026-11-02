import {
  Navigate,
  Outlet,
  useLocation,
} from 'react-router-dom'

import { useAuth } from '../../hooks/useAuth'


interface LoginLocationState {
  from?: unknown
}


function resolveReturnLocation(
  state: unknown,
): string {
  if (
    state === null ||
    typeof state !== 'object'
  ) {
    return '/'
  }

  const {
    from,
  } = state as LoginLocationState

  if (
    typeof from !== 'string' ||
    !from.startsWith('/') ||
    from.startsWith('//')
  ) {
    return '/'
  }

  return from
}


export function PublicOnlyRoute() {
  const auth = useAuth()
  const location = useLocation()

  if (auth.status === 'loading') {
    return (
      <div
        role="status"
        className="auth-loading"
      >
        Restoring AquaMind session...
      </div>
    )
  }

  if (auth.isAuthenticated) {
    return (
      <Navigate
        to={resolveReturnLocation(
          location.state,
        )}
        replace
      />
    )
  }

  return <Outlet />
}