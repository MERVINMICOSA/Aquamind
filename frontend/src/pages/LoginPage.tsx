import {
  type FormEvent,
  useState,
} from 'react'

import { ApiError } from '../services/baseApi'
import { useAuth } from '../hooks/useAuth'


interface LoginFieldErrors {
  username?: string
  password?: string
}


function getLoginErrorMessage(
  error: unknown,
): string {
  if (
    error instanceof ApiError &&
    error.status === 401
  ) {
    return 'Invalid username or password.'
  }

  if (
    error instanceof ApiError
  ) {
    return (
      'AquaMind authentication is currently unavailable.'
    )
  }

  if (
    error instanceof TypeError
  ) {
    return (
      'Unable to reach the AquaMind server.'
    )
  }

  return (
    'Unable to sign in. Please try again.'
  )
}


export function LoginPage() {
  const auth = useAuth()

  const [
    username,
    setUsername,
  ] = useState('')

  const [
    password,
    setPassword,
  ] = useState('')

  const [
    showPassword,
    setShowPassword,
  ] = useState(false)

  const [
    isSubmitting,
    setIsSubmitting,
  ] = useState(false)

  const [
    fieldErrors,
    setFieldErrors,
  ] = useState<LoginFieldErrors>({})

  const [
    submitError,
    setSubmitError,
  ] = useState<string | null>(
    null,
  )


  function validate():
    LoginFieldErrors {
    const errors:
      LoginFieldErrors = {}

    if (!username.trim()) {
      errors.username =
        'Username is required.'
    }

    if (!password) {
      errors.password =
        'Password is required.'
    }

    return errors
  }


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault()

    if (isSubmitting) {
      return
    }

    setSubmitError(
      null,
    )

    const errors =
      validate()

    setFieldErrors(
      errors,
    )

    if (
      errors.username !== undefined ||
      errors.password !== undefined
    ) {
      return
    }

    setIsSubmitting(
      true,
    )

    try {
      await auth.login({
        username:
          username.trim(),

        password,
      })
    } catch (error) {
      setSubmitError(
        getLoginErrorMessage(
          error,
        ),
      )

      setIsSubmitting(
        false,
      )
    }
  }


  return (
    <main className="login-page">
      <section
        className="login-card"
        aria-labelledby="login-title"
      >
        <div className="login-card__header">
          <p className="eyebrow">
            Administrator Access
          </p>

          <h1 id="login-title">
            Sign in to AquaMind
          </h1>

          <p className="login-description">
            Authenticate to access the
            aquaponics management console.
          </p>
        </div>

        {submitError !== null && (
          <div
            role="alert"
            className="login-alert"
          >
            {submitError}
          </div>
        )}

        <form
          className="login-form"
          onSubmit={(event) => {
            void handleSubmit(event)
          }}
          noValidate
        >
          <div className="form-field">
            <label
              htmlFor="username"
              className="form-label"
            >
              Username
            </label>

            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={username}
              disabled={isSubmitting}
              aria-invalid={
                fieldErrors.username !==
                undefined
              }
              aria-describedby={
                fieldErrors.username !==
                undefined
                  ? 'username-error'
                  : undefined
              }
              onChange={(event) => {
                setUsername(
                  event.target.value,
                )

                if (
                  fieldErrors.username !==
                  undefined
                ) {
                  setFieldErrors(
                    (current) => ({
                      ...current,
                      username:
                        undefined,
                    }),
                  )
                }
              }}
            />

            {fieldErrors.username !==
              undefined && (
              <p
                id="username-error"
                className="form-error"
              >
                {fieldErrors.username}
              </p>
            )}
          </div>

          <div className="form-field">
            <label
              htmlFor="password"
              className="form-label"
            >
              Password
            </label>

            <div className="password-field">
              <input
                id="password"
                name="password"
                type={
                  showPassword
                    ? 'text'
                    : 'password'
                }
                autoComplete="current-password"
                value={password}
                disabled={isSubmitting}
                aria-invalid={
                  fieldErrors.password !==
                  undefined
                }
                aria-describedby={
                  fieldErrors.password !==
                  undefined
                    ? 'password-error'
                    : undefined
                }
                onChange={(event) => {
                  setPassword(
                    event.target.value,
                  )

                  if (
                    fieldErrors.password !==
                    undefined
                  ) {
                    setFieldErrors(
                      (current) => ({
                        ...current,
                        password:
                          undefined,
                      }),
                    )
                  }
                }}
              />

              <button
                type="button"
                className="password-toggle"
                disabled={isSubmitting}
                aria-pressed={
                  showPassword
                }
                onClick={() => {
                  setShowPassword(
                    (current) =>
                      !current,
                  )
                }}
              >
                {showPassword
                  ? 'Hide'
                  : 'Show'}
              </button>
            </div>

            {fieldErrors.password !==
              undefined && (
              <p
                id="password-error"
                className="form-error"
              >
                {fieldErrors.password}
              </p>
            )}
          </div>

          <button
            type="submit"
            className="login-submit"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? 'Signing in...'
              : 'Sign in'}
          </button>
        </form>

        <p className="login-security-note">
          AquaMind management access is
          restricted to authorized
          administrators.
        </p>
      </section>
    </main>
  )
}