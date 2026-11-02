import {
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  MemoryRouter,
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
} from '../contexts/authContext'

import { useAuth } from '../hooks/useAuth'
import { ApiError } from '../services/baseApi'
import { LoginPage } from './LoginPage'


vi.mock(
  '../hooks/useAuth',
  () => ({
    useAuth: vi.fn(),
  }),
)


function configureAuth(
  login:
    AuthContextValue['login'],
): void {
  vi.mocked(
    useAuth,
  ).mockReturnValue({
    status:
      'unauthenticated',

    user:
      null,

    isAuthenticated:
      false,

    login,

    logout:
      vi.fn(
        async () =>
          undefined,
      ),
  })
}


function renderLoginPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  )
}


describe(
  'AquaMind login page',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })


    it(
      'renders the administrator login form',
      () => {
        configureAuth(
          vi.fn(
            async () =>
              undefined,
          ),
        )

        renderLoginPage()

        expect(
          screen.getByRole(
            'heading',
            {
              name:
                'Sign in to AquaMind',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByLabelText(
            'Username',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByLabelText(
            'Password',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByRole(
            'button',
            {
              name:
                'Sign in',
            },
          ),
        ).toBeInTheDocument()
      },
    )


    it(
      'validates required credentials before submitting',
      async () => {
        const loginMock =
          vi.fn(
            async () =>
              undefined,
          )

        configureAuth(
          loginMock,
        )

        const user =
          userEvent.setup()

        renderLoginPage()

        await user.click(
          screen.getByRole(
            'button',
            {
              name:
                'Sign in',
            },
          ),
        )

        expect(
          screen.getByText(
            'Username is required.',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'Password is required.',
          ),
        ).toBeInTheDocument()

        expect(
          loginMock,
        ).not.toHaveBeenCalled()
      },
    )


    it(
      'submits normalized credentials',
      async () => {
        const loginMock =
          vi.fn(
            async () =>
              undefined,
          )

        configureAuth(
          loginMock,
        )

        const user =
          userEvent.setup()

        renderLoginPage()

        await user.type(
          screen.getByLabelText(
            'Username',
          ),
          ' admin ',
        )

        await user.type(
          screen.getByLabelText(
            'Password',
          ),
          'secret',
        )

        await user.click(
          screen.getByRole(
            'button',
            {
              name:
                'Sign in',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              loginMock,
            ).toHaveBeenCalledWith({
              username:
                'admin',

              password:
                'secret',
            })
          },
        )
      },
    )


    it(
      'shows the invalid-credentials response from the authentication boundary',
      async () => {
        const loginMock =
          vi.fn(
            async () => {
              throw new ApiError(
                'Authentication failed',
                401,
                JSON.stringify({
                  detail:
                    'Invalid username or password',
                }),
              )
            },
          )

        configureAuth(
          loginMock,
        )

        const user =
          userEvent.setup()

        renderLoginPage()

        await user.type(
          screen.getByLabelText(
            'Username',
          ),
          'admin',
        )

        await user.type(
          screen.getByLabelText(
            'Password',
          ),
          'wrong-password',
        )

        await user.click(
          screen.getByRole(
            'button',
            {
              name:
                'Sign in',
            },
          ),
        )

        expect(
          await screen.findByRole(
            'alert',
          ),
        ).toHaveTextContent(
          'Invalid username or password.',
        )
      },
    )


    it(
      'allows password visibility to be toggled',
      async () => {
        configureAuth(
          vi.fn(
            async () =>
              undefined,
          ),
        )

        const user =
          userEvent.setup()

        renderLoginPage()

        const passwordInput =
          screen.getByLabelText(
            'Password',
          )

        expect(
          passwordInput,
        ).toHaveAttribute(
          'type',
          'password',
        )

        await user.click(
          screen.getByRole(
            'button',
            {
              name:
                'Show',
            },
          ),
        )

        expect(
          passwordInput,
        ).toHaveAttribute(
          'type',
          'text',
        )

        expect(
          screen.getByRole(
            'button',
            {
              name:
                'Hide',
            },
          ),
        ).toBeInTheDocument()
      },
    )
  },
)