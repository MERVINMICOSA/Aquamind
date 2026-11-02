const DEFAULT_APP_TITLE = 'AquaMind'
const DEFAULT_API_URL = 'http://127.0.0.1:8000/api/v1'
const DEFAULT_WS_URL = 'ws://127.0.0.1:8000'

function resolveEnvironmentValue(
  value: string | undefined,
  fallback: string,
): string {
  const normalized = value?.trim()

  return normalized || fallback
}

export const env = {
  appTitle: resolveEnvironmentValue(
    import.meta.env.VITE_APP_TITLE,
    DEFAULT_APP_TITLE,
  ),

  apiUrl: resolveEnvironmentValue(
    import.meta.env.VITE_API_URL,
    DEFAULT_API_URL,
  ),

  wsUrl: resolveEnvironmentValue(
    import.meta.env.VITE_WS_URL,
    DEFAULT_WS_URL,
  ),
} as const