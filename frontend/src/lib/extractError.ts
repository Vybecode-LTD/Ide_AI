/**
 * extractError — Extracts a human-readable error message from an Axios error.
 * Handles FastAPI string details, Pydantic 422 validation arrays, entitlement
 * errors (403 with structured detail), and generic 500s.
 * @module lib/extractError
 */

interface ValidationItem {
  msg?: string
  loc?: (string | number)[]
}

/** Structured detail returned by the entitlement guards (403). */
export interface EntitlementDetail {
  code: 'project_limit_reached' | 'feature_limit_reached'
  feature?: string
  current: number
  limit: number
  plan: string
  message: string
}

/**
 * Check whether an Axios error is an entitlement 403.
 * Returns the structured detail if so, otherwise `null`.
 */
export function getEntitlementDetail(err: unknown): EntitlementDetail | null {
  const resp = (err as { response?: { data?: { detail?: unknown }; status?: number } })?.response
  if (!resp || resp.status !== 403) return null
  const detail = resp.data?.detail
  if (
    detail &&
    typeof detail === 'object' &&
    !Array.isArray(detail) &&
    ('code' in (detail as Record<string, unknown>))
  ) {
    const d = detail as Record<string, unknown>
    if (d.code === 'project_limit_reached' || d.code === 'feature_limit_reached') {
      return detail as EntitlementDetail
    }
  }
  return null
}

/** Convenience: returns true when the error is an entitlement 403. */
export function isEntitlementError(err: unknown): boolean {
  return getEntitlementDetail(err) !== null
}

export function extractError(err: unknown, fallback: string): string {
  const resp = (err as { response?: { data?: { detail?: unknown }; status?: number } })?.response

  // No axios response: it's a network error or a manually-thrown Error.
  // Prefer the Error.message when present, otherwise the fallback.
  if (!resp) {
    const message = (err as { message?: unknown })?.message
    if (typeof message === 'string' && message.trim() && message !== 'Network Error') {
      return message
    }
    if (message === 'Network Error') {
      return 'Network error — please check your connection and try again.'
    }
    return fallback
  }

  const detail = resp.data?.detail

  // Entitlement 403 — return the human-readable message
  const ent = getEntitlementDetail(err)
  if (ent) return ent.message

  // FastAPI string detail (e.g. "Email already registered")
  if (typeof detail === 'string') return detail

  // Pydantic 422 validation errors (detail is an array)
  if (Array.isArray(detail) && detail.length > 0) {
    return (detail as ValidationItem[])
      .map((d) => d.msg || 'Validation error')
      .join('. ')
  }

  // 500 Internal Server Error with no detail
  if (resp.status && resp.status >= 500) return 'Server error. Please try again later.'

  return fallback
}
