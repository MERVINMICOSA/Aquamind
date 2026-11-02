import {
  render,
  screen,
} from '@testing-library/react'
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  checkBackendConnection,
} from '../../services/backendHealthService'
import {
  ConnectionStatus,
} from './ConnectionStatus'


vi.mock(
  '../../services/backendHealthService',
  () => ({
    checkBackendConnection:
      vi.fn(),
  }),
)


describe(
  'backend connection status',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })


    it(
      'shows the backend as online after a successful health check',
      async () => {
        vi.mocked(
          checkBackendConnection,
        ).mockResolvedValueOnce(
          true,
        )

        render(
          <ConnectionStatus />,
        )

        expect(
          await screen.findByText(
            'Backend online',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'shows the backend as offline after a failed health check',
      async () => {
        vi.mocked(
          checkBackendConnection,
        ).mockResolvedValueOnce(
          false,
        )

        render(
          <ConnectionStatus />,
        )

        expect(
          await screen.findByText(
            'Backend offline',
          ),
        ).toBeInTheDocument()
      },
    )
  },
)