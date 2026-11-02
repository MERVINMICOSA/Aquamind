import { env } from '../config/env'

export class ApiError extends Error {
  readonly status: number
  readonly responseBody: string

  constructor(
    message: string,
    status: number,
    responseBody: string,
  ) {
    super(message)

    this.name = 'ApiError'
    this.status = status
    this.responseBody = responseBody
  }
}

export function buildApiUrl(
  path: string,
): string {
  const normalizedBaseUrl =
    env.apiUrl.replace(/\/+$/, '')

  const normalizedPath =
    path.replace(/^\/+/, '')

  return (
    `${normalizedBaseUrl}/` +
    normalizedPath
  )
}

export async function rawApiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers =
    new Headers(init.headers)

  if (!headers.has('Accept')) {
    headers.set(
      'Accept',
      'application/json',
    )
  }

  if (
    init.body !== undefined &&
    !(init.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set(
      'Content-Type',
      'application/json',
    )
  }

  const response = await fetch(
    buildApiUrl(path),
    {
      ...init,
      headers,
    },
  )

  if (!response.ok) {
    const responseBody =
      await response.text()

    throw new ApiError(
      `AquaMind API request failed with status ${response.status}`,
      response.status,
      responseBody,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}