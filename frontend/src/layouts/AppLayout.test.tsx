import {
  render,
  screen,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  MemoryRouter,
  Route,
  Routes,
} from 'react-router-dom'
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import { useAuth } from '../hooks/useAuth'
import { AppLayout } from './AppLayout'


vi.mock(
  '../components/common/ConnectionStatus',
  () => ({
    ConnectionStatus: () => (
      <div>
        Backend online
      </div>
    ),
  }),
)

vi.mock(
  '../hooks/useAuth',
  () => ({
    useAuth: vi.fn(),
  }),
)


const logoutMock =
  vi.fn(
    async () => undefined,
  )


function renderLayout(
  path = '/',
) {
  return render(
    <MemoryRouter
      initialEntries={[
        path,
      ]}
    >
      <Routes>
        <Route
          element={<AppLayout />}
        >
          <Route
            path="*"
            element={
              <div>
                Route content
              </div>
            }
          />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}


describe(
  'AquaMind application shell',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()

      vi.mocked(
        useAuth,
      ).mockReturnValue({
        status:
          'authenticated',

        user: {
          userId:
            '11111111-1111-1111-1111-111111111111',

          username:
            'admin',

          role:
            'admin',

          isActive:
            true,
        },

        isAuthenticated:
          true,

        login:
          vi.fn(
            async () =>
              undefined,
          ),

        logout:
          logoutMock,
      })
    })


    it(
      'renders the documented primary navigation',
      () => {
        renderLayout()

        for (
          const label
          of [
            'Dashboard',
            'Sensors',
            'History',
            'Feeding',
            'Water Flow',
            'Alerts',
            'Settings',
          ]
        ) {
          expect(
            screen.getByRole(
              'link',
              {
                name: label,
              },
            ),
          ).toBeInTheDocument()
        }
      },
    )


    it(
      'marks the current route as active',
      () => {
        renderLayout(
          '/sensors',
        )

        expect(
          screen.getByRole(
            'link',
            {
              name: 'Sensors',
            },
          ),
        ).toHaveAttribute(
          'aria-current',
          'page',
        )
      },
    )


    it(
      'allows the administrator to sign out',
      async () => {
        const user =
          userEvent.setup()

        renderLayout()

        await user.click(
          screen.getByRole(
            'button',
            {
              name:
                'Sign out',
            },
          ),
        )

        expect(
          logoutMock,
        ).toHaveBeenCalledTimes(
          1,
        )
      },
    )
  },
)