export type UserRole = 'admin'

export interface LoginCredentials {
  username: string
  password: string
}

export interface AuthTokenResponse {
  user_id: string
  username: string
  role: UserRole

  access_token: string
  refresh_token: string
  token_type: 'bearer'

  refresh_token_expires_at: string
}

export interface CurrentUserResponse {
  user_id: string
  username: string
  role: UserRole
  is_active: boolean
}

export interface AuthUser {
  userId: string
  username: string
  role: UserRole
  isActive: boolean
}