import {
  clearAuthTokens,
} from './authTokenStore'


type AuthInvalidationListener =
  () => void


const invalidationListeners =
  new Set<AuthInvalidationListener>()


export function subscribeToAuthInvalidation(
  listener: AuthInvalidationListener,
): () => void {
  invalidationListeners.add(
    listener,
  )

  return () => {
    invalidationListeners.delete(
      listener,
    )
  }
}


export function invalidateAuthentication():
  void {
  clearAuthTokens()

  for (
    const listener
    of invalidationListeners
  ) {
    listener()
  }
}