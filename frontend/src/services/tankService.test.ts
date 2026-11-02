import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  apiRequest,
} from './apiClient'

import {
  listSystemTanks,
} from './tankService'


vi.mock(
  './apiClient',
  () => ({
    apiRequest:
      vi.fn(),
  }),
)


const mockedApiRequest =
  vi.mocked(
    apiRequest,
  )


describe(
  'tank service',
  () => {
    beforeEach(() => {
      mockedApiRequest
        .mockReset()
    })


    it(
      'loads tanks scoped to the selected system',
      async () => {
        mockedApiRequest
          .mockResolvedValueOnce(
            [],
          )

        await listSystemTanks(
          'system/1',
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'tanks?system_id=system%2F1',
        )
      },
    )
  },
)