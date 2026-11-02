import { createContext } from 'react'

import type {
  AuthUser,
  LoginCredentials,
} from '../types/auth'

export type AuthStatus =
  | 'loading'
  | 'authenticated'
  | 'unauthenticated'

export interface AuthContextValue {
  status: AuthStatus
  user: AuthUser | null
  isAuthenticated: boolean

  login: (
    credentials: LoginCredentials,
  ) => Promise<void>

  logout: () => Promise<void>
}

export const AuthContext =
  createContext<AuthContextValue | null>(
    null,
  )