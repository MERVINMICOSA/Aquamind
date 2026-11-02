import {
  render,
  screen,
} from '@testing-library/react'
import {
  describe,
  expect,
  it,
} from 'vitest'

import { App } from './App'


describe(
  'AquaMind application',
  () => {
    it(
      'routes an unauthenticated browser session to login',
      async () => {
        sessionStorage.clear()

        render(
          <App />,
        )

        expect(
          await screen.findByRole(
            'heading',
            {
              name:
                'Sign in to AquaMind',
            },
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'Authenticate to access the aquaponics management console.',
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
      },
    )
  },
)