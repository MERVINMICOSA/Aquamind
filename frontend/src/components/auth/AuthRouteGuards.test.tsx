import {
  render,
  screen,
} from '@testing-library/react'
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import type {
  AuthContextValue,
} from '../../contexts/authContext'
import type {
  AuthUser,
} from '../../types/auth'

import { useAuth } from '../../hooks/useAuth'
import { ProtectedRoute } from './ProtectedRoute'
import { PublicOnlyRoute } from './PublicOnlyRoute'


vi.mock(
  '../../hooks/useAuth',
  () => ({
    useAuth: vi.fn(),
  }),
)


const ADMIN_USER: AuthUser = {
  userId:
    '11111111-1111-1111-1111-111111111111',

  username: 'admin',
  role: 'admin',
  isActive: true,
}


function createAuthValue(
  status:
    | 'loading'
    | 'authenticated'
    | 'unauthenticated',
): AuthContextValue {
  const authenticated =
    status === 'authenticated'

  return {
    status,

    user:
      authenticated
        ? ADMIN_USER
        : null,

    isAuthenticated:
      authenticated,

    login: vi.fn(
      async () => undefined,
    ),

    logout: vi.fn(
      async () => undefined,
    ),
  }
}


function LoginProbe() {
  const location =
    useLocation()

  const state =
    location.state as
      | {
          from?: string
        }
      | null

  return (
    <div>
      <div>
        Login page
      </div>

      <div data-testid="return-to">
        {state?.from ?? 'none'}
      </div>
    </div>
  )
}


describe(
  'AquaMind authentication route guards',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })


    it(
      'shows a loading state while authentication is being restored',
      () => {
        vi.mocked(
          useAuth,
        ).mockReturnValue(
          createAuthValue(
            'loading',
          ),
        )

        render(
          <MemoryRouter
            initialEntries={[
              '/dashboard',
            ]}
          >
            <Routes>
              <Route
                element={
                  <ProtectedRoute />
                }
              >
                <Route
                  path="/dashboard"
                  element={
                    <div>
                      Dashboard
                    </div>
                  }
                />
              </Route>
            </Routes>
          </MemoryRouter>,
        )

        expect(
          screen.getByRole(
            'status',
          ),
        ).toHaveTextContent(
          'Restoring AquaMind session...',
        )

        expect(
          screen.queryByText(
            'Dashboard',
          ),
        ).not.toBeInTheDocument()
      },
    )


    it(
      'redirects an unauthenticated user to login and preserves the requested location',
      () => {
        vi.mocked(
          useAuth,
        ).mockReturnValue(
          createAuthValue(
            'unauthenticated',
          ),
        )

        render(
          <MemoryRouter
            initialEntries={[
              '/dashboard?system=1',
            ]}
          >
            <Routes>
              <Route
                element={
                  <ProtectedRoute />
                }
              >
                <Route
                  path="/dashboard"
                  element={
                    <div>
                      Dashboard
                    </div>
                  }
                />
              </Route>

              <Route
                path="/login"
                element={
                  <LoginProbe />
                }
              />
            </Routes>
          </MemoryRouter>,
        )

        expect(
          screen.getByText(
            'Login page',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByTestId(
            'return-to',
          ),
        ).toHaveTextContent(
          '/dashboard?system=1',
        )

        expect(
          screen.queryByText(
            'Dashboard',
          ),
        ).not.toBeInTheDocument()
      },
    )


    it(
      'allows an authenticated user to access a protected route',
      () => {
        vi.mocked(
          useAuth,
        ).mockReturnValue(
          createAuthValue(
            'authenticated',
          ),
        )

        render(
          <MemoryRouter
            initialEntries={[
              '/dashboard',
            ]}
          >
            <Routes>
              <Route
                element={
                  <ProtectedRoute />
                }
              >
                <Route
                  path="/dashboard"
                  element={
                    <div>
                      Dashboard
                    </div>
                  }
                />
              </Route>

              <Route
                path="/login"
                element={
                  <div>
                    Login
                  </div>
                }
              />
            </Routes>
          </MemoryRouter>,
        )

        expect(
          screen.getByText(
            'Dashboard',
          ),
        ).toBeInTheDocument()

        expect(
          screen.queryByText(
            'Login',
          ),
        ).not.toBeInTheDocument()
      },
    )


    it(
      'allows an unauthenticated user to access the login route',
      () => {
        vi.mocked(
          useAuth,
        ).mockReturnValue(
          createAuthValue(
            'unauthenticated',
          ),
        )

        render(
          <MemoryRouter
            initialEntries={[
              '/login',
            ]}
          >
            <Routes>
              <Route
                element={
                  <PublicOnlyRoute />
                }
              >
                <Route
                  path="/login"
                  element={
                    <div>
                      Login
                    </div>
                  }
                />
              </Route>

              <Route
                path="/"
                element={
                  <div>
                    Dashboard
                  </div>
                }
              />
            </Routes>
          </MemoryRouter>,
        )

        expect(
          screen.getByText(
            'Login',
          ),
        ).toBeInTheDocument()
      },
    )


    it(
    'returns an authenticated user to the originally requested protected route',
    () => {
        vi.mocked(
        useAuth,
        ).mockReturnValue(
        createAuthValue(
            'authenticated',
        ),
        )

        render(
        <MemoryRouter
            initialEntries={[
            {
                pathname:
                '/login',

                state: {
                from:
                    '/dashboard?system=1',
                },
            },
            ]}
        >
            <Routes>
            <Route
                element={
                <PublicOnlyRoute />
                }
            >
                <Route
                path="/login"
                element={
                    <div>
                    Login
                    </div>
                }
                />
            </Route>

            <Route
                path="/dashboard"
                element={
                <div>
                    Dashboard
                </div>
                }
            />
            </Routes>
        </MemoryRouter>,
        )

        expect(
        screen.getByText(
            'Dashboard',
        ),
        ).toBeInTheDocument()

        expect(
        screen.queryByText(
            'Login',
        ),
        ).not.toBeInTheDocument()
    },
    )
  },
)