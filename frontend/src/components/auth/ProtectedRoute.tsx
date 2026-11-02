import {
  Navigate,
  Outlet,
  useLocation,
} from 'react-router-dom'

import { useAuth } from '../../hooks/useAuth'


export function ProtectedRoute() {
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

  if (!auth.isAuthenticated) {
    const returnTo =
      `${location.pathname}` +
      `${location.search}` +
      `${location.hash}`

    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: returnTo,
        }}
      />
    )
  }

  return <Outlet />
}