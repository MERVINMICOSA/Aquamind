import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  subscribeToAuthInvalidation,
} from './authSession'
import {
  clearAuthTokens,
  setAccessToken,
} from './authTokenStore'
import {
  apiRequest,
} from './apiClient'


describe(
  'authenticated API client',
  () => {
    beforeEach(() => {
      clearAuthTokens()

      vi.restoreAllMocks()
    })


    it(
      'sends the access token as a bearer token',
      async () => {
        setAccessToken(
          'access-token',
        )

        const fetchSpy =
          vi.spyOn(
            globalThis,
            'fetch',
          ).mockResolvedValueOnce(
            new Response(
              JSON.stringify({
                ok: true,
              }),
              {
                status: 200,

                headers: {
                  'Content-Type':
                    'application/json',
                },
              },
            ),
          )

        await apiRequest<{
          ok: boolean
        }>(
          'systems',
        )

        const requestInit =
          fetchSpy.mock.calls[0]?.[1]

        const headers =
          new Headers(
            requestInit?.headers,
          )

        expect(
          headers.get(
            'Authorization',
          ),
        ).toBe(
          'Bearer access-token',
        )
      },
    )


    it(
      'invalidates authentication when a protected request returns 401 and no refresh token exists',
      async () => {
        setAccessToken(
          'expired-access-token',
        )

        vi.spyOn(
          globalThis,
          'fetch',
        ).mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              detail:
                'Authentication required',
            }),
            {
              status: 401,

              headers: {
                'Content-Type':
                  'application/json',
              },
            },
          ),
        )

        const listener =
          vi.fn()

        const unsubscribe =
          subscribeToAuthInvalidation(
            listener,
          )

        try {
          await expect(
            apiRequest(
              'systems',
            ),
          ).rejects.toMatchObject({
            status: 401,
          })

          expect(
            listener,
          ).toHaveBeenCalledTimes(
            1,
          )
        } finally {
          unsubscribe()
        }
      },
    )
  },
)