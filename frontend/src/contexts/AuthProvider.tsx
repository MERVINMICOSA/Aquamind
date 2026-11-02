import {
  type PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  AuthContext,
  type AuthStatus,
} from './authContext'

import type {
  AuthUser,
  LoginCredentials,
} from '../types/auth'

import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  restoreAuthentication,
} from '../services/authService'

import {
  clearAuthTokens,
} from '../services/authTokenStore'
import {
  subscribeToAuthInvalidation,
} from '../services/authSession'


export function AuthProvider({
  children,
}: PropsWithChildren) {
  const [
    status,
    setStatus,
  ] = useState<AuthStatus>(
    'loading',
  )

  const [
    user,
    setUser,
  ] = useState<AuthUser | null>(
    null,
  )

  // =========================================================
  // SESSION RESTORATION
  // =========================================================

  useEffect(() => {
    let active = true

    async function restoreSession():
      Promise<void> {
      const restoredUser =
        await restoreAuthentication()

      if (!active) {
        return
      }

      if (restoredUser === null) {
        setUser(
          null,
        )

        setStatus(
          'unauthenticated',
        )

        return
      }

      setUser(
        restoredUser,
      )

      setStatus(
        'authenticated',
      )
    }

    void restoreSession()

    return () => {
      active = false
    }
  }, [])

  // =========================================================
  // SESSION INVALIDATION
  // =========================================================

  useEffect(() => {
    return subscribeToAuthInvalidation(
      () => {
        setUser(
          null,
        )

        setStatus(
          'unauthenticated',
        )
      },
    )
  }, [])

  // =========================================================
  // LOGIN
  // =========================================================

  const login =
    useCallback(
      async (
        credentials: LoginCredentials,
      ): Promise<void> => {
        try {
          const tokens =
            await loginRequest(
              credentials,
            )

          // /auth/me remains authoritative for current
          // account state, particularly is_active.
          const currentUser =
            await getCurrentUser(
              tokens.access_token,
            )

          setUser(
            currentUser,
          )

          setStatus(
            'authenticated',
          )
        } catch (error) {
          clearAuthTokens()

          setUser(
            null,
          )

          setStatus(
            'unauthenticated',
          )

          throw error
        }
      },
      [],
    )

  // =========================================================
  // LOGOUT
  // =========================================================

  const logout =
    useCallback(
      async (): Promise<void> => {
        // Change application state immediately.
        setUser(
          null,
        )

        setStatus(
          'unauthenticated',
        )

        await logoutRequest()
      },
      [],
    )

  // =========================================================
  // CONTEXT
  // =========================================================

  const value =
    useMemo(
      () => ({
        status,
        user,

        isAuthenticated:
          status ===
          'authenticated',

        login,
        logout,
      }),
      [
        status,
        user,
        login,
        logout,
      ],
    )

  return (
    <AuthContext.Provider
      value={value}
    >
      {children}
    </AuthContext.Provider>
  )
}