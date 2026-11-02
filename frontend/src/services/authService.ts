import type {
  AuthTokenResponse,
  AuthUser,
  CurrentUserResponse,
  LoginCredentials,
} from '../types/auth'

import {
  ApiError,
  rawApiRequest,
} from './baseApi'
import {
  clearAuthTokens,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from './authTokenStore'
import {
  invalidateAuthentication,
} from './authSession'


let refreshPromise:
  Promise<AuthTokenResponse> | null =
    null


function storeTokenResponse(
  tokens: AuthTokenResponse,
): void {
  setAccessToken(
    tokens.access_token,
  )

  setRefreshToken(
    tokens.refresh_token,
  )
}


function mapCurrentUser(
  response: CurrentUserResponse,
): AuthUser {
  return {
    userId: response.user_id,
    username: response.username,
    role: response.role,
    isActive: response.is_active,
  }
}


export async function login(
  credentials: LoginCredentials,
): Promise<AuthTokenResponse> {
  const username =
    credentials.username.trim()

  if (!username) {
    throw new Error(
      'Username is required.',
    )
  }

  if (!credentials.password) {
    throw new Error(
      'Password is required.',
    )
  }

  const tokens =
    await rawApiRequest<AuthTokenResponse>(
      'auth/login',
      {
        method: 'POST',

        body: JSON.stringify({
          username,
          password:
            credentials.password,
        }),
      },
    )

  storeTokenResponse(
    tokens,
  )

  return tokens
}


async function performRefresh():
  Promise<AuthTokenResponse> {
  const refreshToken =
    getRefreshToken()

  if (refreshToken === null) {
    clearAuthTokens()

    throw new ApiError(
      'No refresh token is available.',
      401,
      '',
    )
  }

  try {
    const tokens =
      await rawApiRequest<AuthTokenResponse>(
        'auth/refresh',
        {
          method: 'POST',

          body: JSON.stringify({
            refresh_token:
              refreshToken,
          }),
        },
      )

    storeTokenResponse(
      tokens,
    )

    return tokens
  } catch (error) {
    invalidateAuthentication()

    throw error
  }
}


export function refreshAuthentication():
  Promise<AuthTokenResponse> {
  if (refreshPromise !== null) {
    return refreshPromise
  }

  refreshPromise =
    performRefresh().finally(
      () => {
        refreshPromise = null
      },
    )

  return refreshPromise
}


export async function getCurrentUser(
  accessToken: string,
): Promise<AuthUser> {
  const response =
    await rawApiRequest<CurrentUserResponse>(
      'auth/me',
      {
        headers: {
          Authorization:
            `Bearer ${accessToken}`,
        },
      },
    )

  return mapCurrentUser(
    response,
  )
}


export async function restoreAuthentication():
  Promise<AuthUser | null> {
  if (getRefreshToken() === null) {
    clearAuthTokens()

    return null
  }

  try {
    const tokens =
      await refreshAuthentication()

    return await getCurrentUser(
      tokens.access_token,
    )
  } catch {
    clearAuthTokens()

    return null
  }
}


export async function logout():
  Promise<void> {
  const refreshToken =
    getRefreshToken()

  /*
   * Local authentication ends immediately.
   * Backend revocation happens afterward.
   */
  invalidateAuthentication()

  if (refreshToken === null) {
    return
  }

  try {
    await rawApiRequest<void>(
      'auth/logout',
      {
        method: 'POST',

        body: JSON.stringify({
          refresh_token:
            refreshToken,
        }),
      },
    )
  } catch {
    /*
     * The user remains locally logged out even if
     * server-side revocation cannot currently be
     * reached.
     */
  }
}