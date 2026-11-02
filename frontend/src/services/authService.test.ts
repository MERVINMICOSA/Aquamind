import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  getAccessToken,
  getRefreshToken,
} from './authTokenStore'
import {
  login,
  logout,
  refreshAuthentication,
  restoreAuthentication,
} from './authService'


const TOKEN_RESPONSE = {
  user_id:
    '11111111-1111-1111-1111-111111111111',

  username: 'admin',
  role: 'admin' as const,

  access_token:
    'access-token-1',

  refresh_token:
    'refresh-token-1',

  token_type:
    'bearer' as const,

  refresh_token_expires_at:
    '2026-09-12T00:00:00Z',
}


function jsonResponse(
  value: unknown,
  status = 200,
): Response {
  return new Response(
    JSON.stringify(value),
    {
      status,
      headers: {
        'Content-Type':
          'application/json',
      },
    },
  )
}


describe(
  'authentication service',
  () => {
    beforeEach(() => {
      sessionStorage.clear()

      vi.restoreAllMocks()
    })

    afterEach(() => {
      sessionStorage.clear()
    })


    it(
      'stores authentication tokens after login',
      async () => {
        vi.spyOn(
          globalThis,
          'fetch',
        ).mockResolvedValueOnce(
          jsonResponse(
            TOKEN_RESPONSE,
          ),
        )

        await login({
          username: 'admin',
          password: 'secret',
        })

        expect(
          getAccessToken(),
        ).toBe(
          'access-token-1',
        )

        expect(
          getRefreshToken(),
        ).toBe(
          'refresh-token-1',
        )
      },
    )


    it(
      'rotates the refresh token',
      async () => {
        sessionStorage.setItem(
          'aquamind.refresh_token',
          'old-refresh-token',
        )

        vi.spyOn(
          globalThis,
          'fetch',
        ).mockResolvedValueOnce(
          jsonResponse({
            ...TOKEN_RESPONSE,

            access_token:
              'access-token-2',

            refresh_token:
              'refresh-token-2',
          }),
        )

        await refreshAuthentication()

        expect(
          getAccessToken(),
        ).toBe(
          'access-token-2',
        )

        expect(
          getRefreshToken(),
        ).toBe(
          'refresh-token-2',
        )
      },
    )


    it(
      'deduplicates concurrent refresh requests',
      async () => {
        sessionStorage.setItem(
          'aquamind.refresh_token',
          'refresh-token-1',
        )

        let resolveFetch:
          ((value: Response) => void)
          | undefined

        const fetchPromise =
          new Promise<Response>(
            (resolve) => {
              resolveFetch = resolve
            },
          )

        const fetchSpy =
          vi.spyOn(
            globalThis,
            'fetch',
          ).mockReturnValue(
            fetchPromise,
          )

        const first =
          refreshAuthentication()

        const second =
          refreshAuthentication()

        expect(
          fetchSpy,
        ).toHaveBeenCalledTimes(
          1,
        )

        resolveFetch?.(
          jsonResponse(
            TOKEN_RESPONSE,
          ),
        )

        await Promise.all([
          first,
          second,
        ])

        expect(
          fetchSpy,
        ).toHaveBeenCalledTimes(
          1,
        )
      },
    )


    it(
      'restores a session through refresh and current-user lookup',
      async () => {
        sessionStorage.setItem(
          'aquamind.refresh_token',
          'refresh-token-1',
        )

        const fetchSpy =
          vi.spyOn(
            globalThis,
            'fetch',
          )

        fetchSpy
          .mockResolvedValueOnce(
            jsonResponse(
              TOKEN_RESPONSE,
            ),
          )
          .mockResolvedValueOnce(
            jsonResponse({
              user_id:
                TOKEN_RESPONSE.user_id,

              username:
                'admin',

              role:
                'admin',

              is_active:
                true,
            }),
          )

        const user =
          await restoreAuthentication()

        expect(user).toEqual({
          userId:
            TOKEN_RESPONSE.user_id,

          username:
            'admin',

          role:
            'admin',

          isActive:
            true,
        })

        expect(
          fetchSpy,
        ).toHaveBeenCalledTimes(
          2,
        )
      },
    )


    it(
      'clears local authentication during logout',
      async () => {
        sessionStorage.setItem(
          'aquamind.refresh_token',
          'refresh-token-1',
        )

        vi.spyOn(
          globalThis,
          'fetch',
        ).mockResolvedValueOnce(
          new Response(
            null,
            {
              status: 204,
            },
          ),
        )

        await logout()

        expect(
          getAccessToken(),
        ).toBeNull()

        expect(
          getRefreshToken(),
        ).toBeNull()
      },
    )
  },
)