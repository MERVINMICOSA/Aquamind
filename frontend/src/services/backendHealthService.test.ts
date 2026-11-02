import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  checkBackendConnection,
  getBackendHealthUrl,
} from './backendHealthService'


describe(
  'backend health service',
  () => {
    beforeEach(() => {
      vi.restoreAllMocks()
    })


    it(
      'targets the AquaMind root health endpoint',
      () => {
        expect(
          getBackendHealthUrl(),
        ).toBe(
          'http://127.0.0.1:8000/health',
        )
      },
    )


    it(
      'reports the backend as online for a successful health response',
      async () => {
        vi.spyOn(
          globalThis,
          'fetch',
        ).mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              status: 'ok',
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

        await expect(
          checkBackendConnection(),
        ).resolves.toBe(
          true,
        )
      },
    )


    it(
      'reports the backend as offline when the request fails',
      async () => {
        vi.spyOn(
          globalThis,
          'fetch',
        ).mockRejectedValueOnce(
          new TypeError(
            'Network unavailable',
          ),
        )

        await expect(
          checkBackendConnection(),
        ).resolves.toBe(
          false,
        )
      },
    )
  },
)