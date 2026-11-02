import { env } from '../config/env'


const HEALTH_CHECK_TIMEOUT_MS = 5_000


export function getBackendHealthUrl():
  string {
  const apiUrl = new URL(
    env.apiUrl,
    window.location.origin,
  )

  return new URL(
    '/health',
    apiUrl,
  ).toString()
}


export async function checkBackendConnection():
  Promise<boolean> {
  const controller =
    new AbortController()

  const timeoutId =
    window.setTimeout(
      () => {
        controller.abort()
      },
      HEALTH_CHECK_TIMEOUT_MS,
    )

  try {
    const response =
      await fetch(
        getBackendHealthUrl(),
        {
          method: 'GET',

          headers: {
            Accept:
              'application/json',
          },

          cache: 'no-store',
          credentials: 'omit',
          signal:
            controller.signal,
        },
      )

    return response.ok
  } catch {
    return false
  } finally {
    window.clearTimeout(
      timeoutId,
    )
  }
}