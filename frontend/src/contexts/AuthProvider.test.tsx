import {
  screen,
  render,
  waitFor,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import type {
  AuthUser,
} from '../types/auth'

import {
  AuthProvider,
} from './AuthProvider'
import {
  useAuth,
} from '../hooks/useAuth'

import {
  getCurrentUser,
  login,
  logout,
  restoreAuthentication,
} from '../services/authService'

import {
  invalidateAuthentication,
} from '../services/authSession'


vi.mock(
  '../services/authService',
  () => ({
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    restoreAuthentication: vi.fn(),
  }),
)


const ADMIN_USER: AuthUser = {
  userId:
    '11111111-1111-1111-1111-111111111111',

  username: 'admin',
  role: 'admin',
  isActive: true,
}


const TOKEN_RESPONSE = {
  user_id:
    ADMIN_USER.userId,

  username:
    ADMIN_USER.username,

  role:
    'admin' as const,

  access_token:
    'access-token',

  refresh_token:
    'refresh-token',

  token_type:
    'bearer' as const,

  refresh_token_expires_at:
    '2026-09-13T00:00:00Z',
}


function AuthProbe() {
  const auth =
    useAuth()

  return (
    <div>
      <div data-testid="status">
        {auth.status}
      </div>

      <div data-testid="username">
        {auth.user?.username ?? 'none'}
      </div>

      <div data-testid="authenticated">
        {String(
          auth.isAuthenticated,
        )}
      </div>

      <button
        type="button"
        onClick={() => {
          void auth.login({
            username: 'admin',
            password: 'secret',
          })
        }}
      >
        Login
      </button>

      <button
        type="button"
        onClick={() => {
          void auth.logout()
        }}
      >
        Logout
      </button>
    </div>
  )
}


describe(
  'AuthProvider',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()

      vi.mocked(
        restoreAuthentication,
      ).mockResolvedValue(
        null,
      )

      vi.mocked(
        logout,
      ).mockResolvedValue(
        undefined,
      )
    })


    it(
      'restores an authenticated session',
      async () => {
        vi.mocked(
          restoreAuthentication,
        ).mockResolvedValueOnce(
          ADMIN_USER,
        )

        render(
          <AuthProvider>
            <AuthProbe />
          </AuthProvider>,
        )

        await waitFor(
          () => {
            expect(
              screen.getByTestId(
                'status',
              ),
            ).toHaveTextContent(
              'authenticated',
            )
          },
        )

        expect(
          screen.getByTestId(
            'username',
          ),
        ).toHaveTextContent(
          'admin',
        )

        expect(
          screen.getByTestId(
            'authenticated',
          ),
        ).toHaveTextContent(
          'true',
        )
      },
    )


    it(
      'becomes unauthenticated when no session can be restored',
      async () => {
        render(
          <AuthProvider>
            <AuthProbe />
          </AuthProvider>,
        )

        await waitFor(
          () => {
            expect(
              screen.getByTestId(
                'status',
              ),
            ).toHaveTextContent(
              'unauthenticated',
            )
          },
        )

        expect(
          screen.getByTestId(
            'username',
          ),
        ).toHaveTextContent(
          'none',
        )
      },
    )


    it(
      'logs in and loads the authoritative current user',
      async () => {
        vi.mocked(
          login,
        ).mockResolvedValueOnce(
          TOKEN_RESPONSE,
        )

        vi.mocked(
          getCurrentUser,
        ).mockResolvedValueOnce(
          ADMIN_USER,
        )

        const user =
          userEvent.setup()

        render(
          <AuthProvider>
            <AuthProbe />
          </AuthProvider>,
        )

        await waitFor(
          () => {
            expect(
              screen.getByTestId(
                'status',
              ),
            ).toHaveTextContent(
              'unauthenticated',
            )
          },
        )

        await user.click(
          screen.getByRole(
            'button',
            {
              name: 'Login',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              screen.getByTestId(
                'status',
              ),
            ).toHaveTextContent(
              'authenticated',
            )
          },
        )

        expect(
          login,
        ).toHaveBeenCalledWith({
          username: 'admin',
          password: 'secret',
        })

        expect(
          getCurrentUser,
        ).toHaveBeenCalledWith(
          'access-token',
        )

        expect(
          screen.getByTestId(
            'username',
          ),
        ).toHaveTextContent(
          'admin',
        )
      },
    )


    it(
      'clears application authentication state on logout',
      async () => {
        vi.mocked(
          restoreAuthentication,
        ).mockResolvedValueOnce(
          ADMIN_USER,
        )

        const user =
          userEvent.setup()

        render(
          <AuthProvider>
            <AuthProbe />
          </AuthProvider>,
        )

        await waitFor(
          () => {
            expect(
              screen.getByTestId(
                'status',
              ),
            ).toHaveTextContent(
              'authenticated',
            )
          },
        )

        await user.click(
          screen.getByRole(
            'button',
            {
              name: 'Logout',
            },
          ),
        )

        expect(
          screen.getByTestId(
            'status',
          ),
        ).toHaveTextContent(
          'unauthenticated',
        )

        expect(
          screen.getByTestId(
            'username',
          ),
        ).toHaveTextContent(
          'none',
        )

        expect(
          logout,
        ).toHaveBeenCalledTimes(
          1,
        )
      },
    )

    it(
      'becomes unauthenticated when the session is invalidated',
      async () => {
        vi.mocked(
          restoreAuthentication,
        ).mockResolvedValueOnce(
          ADMIN_USER,
        )

        render(
          <AuthProvider>
            <AuthProbe />
          </AuthProvider>,
        )

        await waitFor(
          () => {
            expect(
              screen.getByTestId(
                'status',
              ),
            ).toHaveTextContent(
              'authenticated',
            )
          },
        )

        invalidateAuthentication()

        await waitFor(
          () => {
            expect(
              screen.getByTestId(
                'status',
              ),
            ).toHaveTextContent(
              'unauthenticated',
            )
          },
        )

        expect(
          screen.getByTestId(
            'username',
          ),
        ).toHaveTextContent(
          'none',
        )
      },
    )
  },
)