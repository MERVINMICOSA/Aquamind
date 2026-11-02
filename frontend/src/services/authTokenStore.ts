const REFRESH_TOKEN_KEY =
  'aquamind.refresh_token'

let accessToken: string | null = null

export function getAccessToken():
  string | null {
  return accessToken
}

export function setAccessToken(
  token: string,
): void {
  const normalized = token.trim()

  if (!normalized) {
    throw new Error(
      'Access token cannot be empty.',
    )
  }

  accessToken = normalized
}

export function clearAccessToken(): void {
  accessToken = null
}

export function getRefreshToken():
  string | null {
  const token = sessionStorage.getItem(
    REFRESH_TOKEN_KEY,
  )

  const normalized = token?.trim()

  return normalized || null
}

export function setRefreshToken(
  token: string,
): void {
  const normalized = token.trim()

  if (!normalized) {
    throw new Error(
      'Refresh token cannot be empty.',
    )
  }

  sessionStorage.setItem(
    REFRESH_TOKEN_KEY,
    normalized,
  )
}

export function clearRefreshToken(): void {
  sessionStorage.removeItem(
    REFRESH_TOKEN_KEY,
  )
}

export function clearAuthTokens(): void {
  clearAccessToken()
  clearRefreshToken()
}