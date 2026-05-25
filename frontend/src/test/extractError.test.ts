import { describe, it, expect } from 'vitest'
import { extractError, getEntitlementDetail, isEntitlementError } from '../lib/extractError'

describe('extractError', () => {
  it('returns fallback for null/undefined', () => {
    expect(extractError(null, 'oops')).toBe('oops')
    expect(extractError(undefined, 'oops')).toBe('oops')
  })

  it('returns Error.message when no response', () => {
    const err = new Error('Something broke')
    expect(extractError(err, 'fallback')).toBe('Something broke')
  })

  it('returns friendly message for Network Error', () => {
    const err = new Error('Network Error')
    expect(extractError(err, 'fallback')).toBe(
      'Network error — please check your connection and try again.',
    )
  })

  it('returns string detail from response', () => {
    const err = { response: { status: 400, data: { detail: 'Email already registered' } } }
    expect(extractError(err, 'fallback')).toBe('Email already registered')
  })

  it('joins pydantic 422 validation errors', () => {
    const err = {
      response: {
        status: 422,
        data: {
          detail: [
            { msg: 'field required', loc: ['body', 'name'] },
            { msg: 'invalid email', loc: ['body', 'email'] },
          ],
        },
      },
    }
    expect(extractError(err, 'fallback')).toBe('field required. invalid email')
  })

  it('returns server error message for 500+', () => {
    const err = { response: { status: 500, data: {} } }
    expect(extractError(err, 'fallback')).toBe('Server error. Please try again later.')
  })

  it('returns entitlement message for 403 with code', () => {
    const err = {
      response: {
        status: 403,
        data: {
          detail: {
            code: 'project_limit_reached',
            current: 3,
            limit: 3,
            plan: 'free',
            message: 'You have reached the project limit for your plan.',
          },
        },
      },
    }
    expect(extractError(err, 'fallback')).toBe(
      'You have reached the project limit for your plan.',
    )
  })

  it('returns fallback for empty error with no useful info', () => {
    const err = { response: { status: 400, data: {} } }
    expect(extractError(err, 'fallback')).toBe('fallback')
  })
})

describe('getEntitlementDetail', () => {
  it('returns null for non-403', () => {
    const err = { response: { status: 400, data: { detail: { code: 'project_limit_reached' } } } }
    expect(getEntitlementDetail(err)).toBeNull()
  })

  it('returns null for 403 without code', () => {
    const err = { response: { status: 403, data: { detail: 'Forbidden' } } }
    expect(getEntitlementDetail(err)).toBeNull()
  })

  it('returns detail for project_limit_reached', () => {
    const detail = {
      code: 'project_limit_reached' as const,
      current: 3,
      limit: 3,
      plan: 'free',
      message: 'Limit reached',
    }
    const err = { response: { status: 403, data: { detail } } }
    expect(getEntitlementDetail(err)).toEqual(detail)
  })

  it('returns detail for feature_limit_reached', () => {
    const detail = {
      code: 'feature_limit_reached' as const,
      feature: 'prompt_kit',
      current: 5,
      limit: 5,
      plan: 'basic',
      message: 'Feature limit',
    }
    const err = { response: { status: 403, data: { detail } } }
    expect(getEntitlementDetail(err)).toEqual(detail)
  })
})

describe('isEntitlementError', () => {
  it('returns true for entitlement 403', () => {
    const err = {
      response: {
        status: 403,
        data: {
          detail: { code: 'project_limit_reached', current: 1, limit: 1, plan: 'free', message: 'x' },
        },
      },
    }
    expect(isEntitlementError(err)).toBe(true)
  })

  it('returns false for regular 403', () => {
    const err = { response: { status: 403, data: { detail: 'Not allowed' } } }
    expect(isEntitlementError(err)).toBe(false)
  })
})
