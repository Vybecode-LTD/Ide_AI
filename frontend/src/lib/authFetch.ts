/**
 * authFetch.ts -- Token-aware fetch/SSE helpers.
 *
 * Centralizes the pattern of "get Clerk token, attach as Bearer header,
 * throw if auth isn't ready" so callers don't reimplement it everywhere.
 */
import { getAuthToken } from './apiClient'

/**
 * Wrapper around `fetch` that injects the current Clerk session token.
 * Throws if no token is available (user not signed in or Clerk not ready).
 */
export async function authFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const token = await getAuthToken()
  if (!token) throw new Error('Authentication is not ready')
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${token}`)
  return fetch(input, { ...init, headers })
}

/**
 * Build an auth headers dict, returning an empty object when no token is
 * available (useful for optional-auth endpoints like shared project views).
 */
export async function optionalAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAuthToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}
