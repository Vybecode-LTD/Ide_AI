import { describe, it, expect, vi, beforeEach } from 'vitest'
import type * as SentryNamespace from '@sentry/react'
import {
  initErrorTracking,
  reportError,
  resetErrorTrackingForTests,
  scrubBreadcrumb,
  scrubEvent,
  scrubUrl,
  type ScrubbableEvent,
} from '../lib/errorTracking'

type Sentry = typeof SentryNamespace

function fakeSentry() {
  const init = vi.fn()
  const captureException = vi.fn()
  return { sdk: { init, captureException } as unknown as Sentry, init, captureException }
}

beforeEach(() => {
  resetErrorTrackingForTests()
})

describe('scrubUrl', () => {
  it('masks share-link tokens', () => {
    expect(scrubUrl('https://myide.ai/shared/Zx81kLm_secret-token')).toBe('https://myide.ai/shared/[token]')
    expect(scrubUrl('/shared/abc123/comments')).toBe('/shared/[token]/comments')
  })

  it('masks share tokens in the public sharing API, the URLs fetch breadcrumbs record', () => {
    const api = 'https://backend-production-9c212.up.railway.app/api/v1'
    expect(scrubUrl(`${api}/sharing/public/Zx81kLm_secret-token`)).toBe(`${api}/sharing/public/[token]`)
    for (const sub of ['comments', 'ratings', 'verify', 'csv']) {
      expect(scrubUrl(`${api}/sharing/public/tok9/${sub}`)).toBe(`${api}/sharing/public/[token]/${sub}`)
    }
    expect(scrubUrl('/sharing/public/tok9/csv')).toBe('/sharing/public/[token]/csv')
  })

  it('drops query strings and fragments', () => {
    expect(scrubUrl('https://myide.ai/settings?code=oauth-code&state=s#tab')).toBe('https://myide.ai/settings')
    expect(scrubUrl('/discovery/42#message-7')).toBe('/discovery/42')
  })

  it('leaves ordinary paths alone', () => {
    expect(scrubUrl('https://myide.ai/design-kit/0b1c')).toBe('https://myide.ai/design-kit/0b1c')
  })
})

describe('scrubEvent', () => {
  it('keeps only a scrubbed URL from the request and drops user data', () => {
    const event: ScrubbableEvent = {
      request: {
        url: 'https://myide.ai/shared/tok123?ref=email',
        cookies: { __session: 'jwt' },
        headers: { Authorization: 'Bearer jwt' },
        data: { content: 'my secret startup idea' },
        query_string: 'ref=email',
      },
      user: { email: 'someone@example.com', ip_address: '203.0.113.9' },
    }
    const out = scrubEvent(event)
    expect(out.request).toEqual({ url: 'https://myide.ai/shared/[token]' })
    expect(out.user).toBeUndefined()
    expect(JSON.stringify(out)).not.toMatch(/jwt|secret startup|someone@|203\.0\.113/)
  })

  it('drops console and DOM breadcrumbs and scrubs URLs in the rest', () => {
    const out = scrubEvent({
      breadcrumbs: [
        { category: 'console', message: 'draft: my secret startup idea' },
        { category: 'fetch', data: { url: 'https://api.example/x?token=abc', method: 'GET', status_code: 200 } },
        { category: 'navigation', data: { from: '/shared/tok1', to: '/home?x=1' } },
        { category: 'ui.click', message: 'button.send' },
      ],
    })
    expect(out.breadcrumbs).toEqual([
      { category: 'fetch', data: { url: 'https://api.example/x', method: 'GET', status_code: 200 } },
      { category: 'navigation', data: { from: '/shared/[token]', to: '/home' } },
    ])
  })

  it('drops click and input breadcrumbs, whose messages carry aria-labels with project content', () => {
    // The SDK writes the clicked element as a selector with its aria-label, and the
    // Blocks board labels its buttons with the block's name.
    const click = { category: 'ui.click', message: 'div.board > button[aria-label="Delete Acme payroll AI"]' }
    const input = { category: 'ui.input', message: 'textarea[name="idea"][title="Acme payroll AI"]' }
    expect(scrubBreadcrumb(click)).toBeNull()
    expect(scrubBreadcrumb(input)).toBeNull()
    const out = scrubEvent({ breadcrumbs: [click, input] })
    expect(JSON.stringify(out)).not.toContain('Acme payroll AI')
  })

  it('masks the share token in fetch and xhr breadcrumbs from a shared project page', () => {
    const api = 'https://backend-production-9c212.up.railway.app/api/v1'
    const fetchCrumb = scrubBreadcrumb({
      category: 'fetch',
      data: { url: `${api}/sharing/public/Zx81kLm_secret-token`, method: 'GET', status_code: 200 },
    })
    const xhrCrumb = scrubBreadcrumb({
      category: 'xhr',
      data: { url: `/sharing/public/Zx81kLm_secret-token/csv`, method: 'GET' },
    })
    expect(fetchCrumb?.data?.url).toBe(`${api}/sharing/public/[token]`)
    expect(xhrCrumb?.data?.url).toBe('/sharing/public/[token]/csv')
    expect(JSON.stringify([fetchCrumb, xhrCrumb])).not.toContain('Zx81kLm_secret-token')
  })

  it('scrubBreadcrumb returns null only for console and DOM crumbs', () => {
    expect(scrubBreadcrumb({ category: 'console', message: 'x' })).toBeNull()
    expect(scrubBreadcrumb({ category: 'ui.click', message: 'x' })).toBeNull()
    expect(scrubBreadcrumb({ category: 'xhr' })).toEqual({ category: 'xhr' })
  })
})

describe('initErrorTracking', () => {
  it('does nothing without a DSN, and never loads the SDK', async () => {
    const load = vi.fn()
    await expect(initErrorTracking('', load)).resolves.toBeNull()
    await expect(initErrorTracking(undefined, load)).resolves.toBeNull()
    expect(load).not.toHaveBeenCalled()
    reportError(new Error('ignored')) // must not throw
  })

  it('loads once and starts Sentry with privacy settings', async () => {
    const { sdk, init } = fakeSentry()
    const load = vi.fn(async () => sdk)
    await initErrorTracking('https://key@o1.ingest.us.sentry.io/2', load)
    await initErrorTracking('https://key@o1.ingest.us.sentry.io/2', load)
    expect(load).toHaveBeenCalledTimes(1)
    expect(init).toHaveBeenCalledTimes(1)
    const options = init.mock.calls[0][0]
    expect(options.dsn).toBe('https://key@o1.ingest.us.sentry.io/2')
    expect(options.sendDefaultPii).toBe(false)
    expect(options.tracesSampleRate).toBeUndefined()
    expect(options.integrations).toBeUndefined() // no replay or tracing added
    const scrubbed = options.beforeSend({ request: { url: '/shared/t?q=1', data: 'body' } })
    expect(scrubbed.request).toEqual({ url: '/shared/[token]' })
    expect(options.beforeBreadcrumb({ category: 'console', message: 'x' })).toBeNull()
  })

  it('sends an error reported while the SDK is still loading', async () => {
    const { sdk, captureException } = fakeSentry()
    let finish: (s: Sentry) => void = () => {}
    const pending = initErrorTracking('https://key@o1.ingest.sentry.io/2', () => new Promise((r) => (finish = r)))
    const error = new Error('render failed')
    reportError(error, { componentStack: '\n at Broken' })
    expect(captureException).not.toHaveBeenCalled()
    finish(sdk)
    await pending
    await Promise.resolve()
    expect(captureException).toHaveBeenCalledWith(error, { extra: { componentStack: '\n at Broken' } })
  })

  it('survives an SDK that fails to load', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    await expect(initErrorTracking('https://key@o1.ingest.sentry.io/2', () => Promise.reject(new Error('blocked')))).resolves.toBeNull()
    reportError(new Error('after a failed load')) // must not throw
    await Promise.resolve()
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })
})
