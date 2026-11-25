/**
 * errorTracking — browser error reporting through Sentry.
 *
 * Off unless `VITE_SENTRY_DSN` is set when the frontend is built (Vite bakes
 * `VITE_*` values in at build time; see frontend/Dockerfile). The SDK is a
 * dynamic import, so a build without a DSN never downloads it.
 *
 * What leaves the browser is kept to the error itself: no default personal
 * data, no session replay, no tracing, no request bodies, cookies or headers,
 * no console breadcrumbs (they can hold a user's text), no click or input
 * breadcrumbs (the SDK records the element's aria-label, name and title, and
 * the Blocks board puts block names in aria-labels), and every URL loses
 * its query string and fragment, with share-link tokens masked (in the page
 * URL `/shared/<token>` and in the public API URL `/sharing/public/<token>`
 * that a shared project's fetches record as breadcrumbs).
 * @module lib/errorTracking
 */
import type * as SentryNamespace from '@sentry/react'

type Sentry = typeof SentryNamespace
type Loader = () => Promise<Sentry>

/** The parts of a Sentry event this module scrubs. */
export interface ScrubbableEvent {
  request?: {
    url?: string
    cookies?: unknown
    data?: unknown
    headers?: unknown
    query_string?: unknown
  }
  user?: unknown
  breadcrumbs?: ScrubbableBreadcrumb[]
}

export interface ScrubbableBreadcrumb {
  category?: string
  message?: string
  data?: { [key: string]: unknown }
}

const SHARE_TOKEN = /\/(shared|sharing\/public)\/[^/?#]+/g
const URL_FIELDS = ['url', 'from', 'to'] as const

let loading: Promise<Sentry | null> | null = null

/** Drop the query string and fragment, and mask share-link tokens. */
export function scrubUrl(url: string): string {
  const [withoutQuery] = url.split(/[?#]/, 1)
  return withoutQuery.replace(SHARE_TOKEN, '/$1/[token]')
}

/** Remove request payloads, user data and URL secrets from an event. */
export function scrubEvent<T extends ScrubbableEvent>(event: T): T {
  if (event.request) {
    const { url } = event.request
    event.request = url ? { url: scrubUrl(url) } : {}
  }
  delete event.user
  if (event.breadcrumbs) {
    event.breadcrumbs = event.breadcrumbs
      .map((crumb) => scrubBreadcrumb(crumb))
      .filter((crumb): crumb is ScrubbableBreadcrumb => crumb !== null)
  }
  return event
}

/** Drop console and DOM (`ui.*`) breadcrumbs; scrub URLs in the rest. */
export function scrubBreadcrumb<T extends ScrubbableBreadcrumb>(crumb: T): T | null {
  if (crumb.category === 'console' || crumb.category?.startsWith('ui.')) return null
  if (crumb.data) {
    const data = { ...crumb.data }
    for (const field of URL_FIELDS) {
      const value = data[field]
      if (typeof value === 'string') data[field] = scrubUrl(value)
    }
    crumb.data = data
  }
  if (crumb.category === 'navigation' && crumb.message) {
    crumb.message = scrubUrl(crumb.message)
  }
  return crumb
}

/**
 * Load and start Sentry when a DSN is configured. Safe to call more than once;
 * resolves to null when tracking is off or the SDK fails to load.
 */
export function initErrorTracking(
  dsn: string | undefined = import.meta.env.VITE_SENTRY_DSN,
  load: Loader = () => import('@sentry/react'),
): Promise<Sentry | null> {
  if (!dsn) return Promise.resolve(null)
  if (!loading) {
    loading = load()
      .then((sentry) => {
        sentry.init({
          dsn,
          environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE,
          release: import.meta.env.VITE_RELEASE || undefined,
          sendDefaultPii: false,
          beforeSend: (event) => scrubEvent(event),
          beforeBreadcrumb: (crumb) => scrubBreadcrumb(crumb),
        })
        return sentry
      })
      .catch((err: unknown) => {
        console.warn('Error tracking could not load:', err)
        return null
      })
  }
  return loading
}

/**
 * Report an error that never reaches `window.onerror` (React render errors).
 * Does nothing unless initErrorTracking has been called with a DSN; an error
 * reported while the SDK is still loading is sent once it has loaded.
 */
export function reportError(error: unknown, extra?: Record<string, unknown>): void {
  if (!loading) return
  void loading.then((sentry) => {
    sentry?.captureException(error, extra ? { extra } : undefined)
  })
}

/** Tests only: forget a previous initErrorTracking call. */
export function resetErrorTrackingForTests(): void {
  loading = null
}
