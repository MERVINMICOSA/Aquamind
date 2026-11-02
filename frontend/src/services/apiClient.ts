import {
  refreshAuthentication,
} from './authService'
import {
  invalidateAuthentication,
} from './authSession'
import {
  ApiError,
  rawApiRequest,
} from './baseApi'
import {
  getAccessToken,
  getRefreshToken,
} from './authTokenStore'


interface ApiRequestOptions
  extends RequestInit {
  authenticated?: boolean
}


function isUnauthorized(
  error: unknown,
): error is ApiError {
  return (
    error instanceof ApiError &&
    error.status === 401
  )
}


export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    authenticated = true,
    ...init
  } = options

  if (!authenticated) {
    return rawApiRequest<T>(
      path,
      init,
    )
  }


  const execute = (
    accessToken: string | null,
  ) => {
    const headers =
      new Headers(init.headers)

    if (accessToken !== null) {
      headers.set(
        'Authorization',
        `Bearer ${accessToken}`,
      )
    }

    return rawApiRequest<T>(
      path,
      {
        ...init,
        headers,
      },
    )
  }


  try {
    return await execute(
      getAccessToken(),
    )
  } catch (error) {
    if (!isUnauthorized(error)) {
      throw error
    }

    /*
     * A protected request returned 401.
     *
     * If no refresh token exists, there is no valid
     * authentication recovery path.
     */
    if (getRefreshToken() === null) {
      invalidateAuthentication()

      throw error
    }


    /*
     * Refresh authentication.
     *
     * refreshAuthentication() handles refresh-token
     * rotation and invalidates the local session if
     * the refresh itself fails.
     */
    const tokens =
      await refreshAuthentication()


    /*
     * Retry the original request exactly once with
     * the new access token.
     */
    try {
      return await execute(
        tokens.access_token,
      )
    } catch (retryError) {
      /*
       * A second 401 means the freshly issued access
       * token cannot authorize the request. Do not
       * leave React displaying an authenticated state.
       */
      if (isUnauthorized(retryError)) {
        invalidateAuthentication()
      }

      throw retryError
    }
  }
}