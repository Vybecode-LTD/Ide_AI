/**
 * The deploy files that decide whether error tracking can work at all: the
 * Dockerfile must pass VITE_SENTRY_DSN into the build (Vite bakes it in), and
 * the Caddyfile's CSP must let the browser reach Sentry's ingest hosts.
 * Both were missing until 2026-11-24 (audit H-3), so a DSN set in Railway
 * would have done nothing.
 */
import { describe, it, expect } from 'vitest'
import dockerfile from '../../Dockerfile?raw'
import caddyfile from '../../Caddyfile?raw'

function cspDirective(name: string): string[] {
  const csp = caddyfile.match(/Content-Security-Policy "([^"]+)"/)?.[1] ?? ''
  const directive = csp.split(';').map((d) => d.trim()).find((d) => d.startsWith(`${name} `))
  return directive ? directive.split(/\s+/).slice(1) : []
}

/** CSP host-source matching for https sources: exact host, or *.suffix at any depth. */
function allows(sources: string[], url: string): boolean {
  const { protocol, host } = new URL(url)
  return sources.some((source) => {
    const match = source.match(/^https:\/\/(\*\.)?([^/:]+)$/)
    if (!match || protocol !== 'https:') return false
    const [, wildcard, sourceHost] = match
    return wildcard ? host.endsWith(`.${sourceHost}`) : host === sourceHost
  })
}

describe('frontend/Dockerfile', () => {
  const buildAt = dockerfile.indexOf('RUN npm run build')

  it('passes VITE_SENTRY_DSN into the build', () => {
    const arg = dockerfile.indexOf('ARG VITE_SENTRY_DSN')
    const env = dockerfile.indexOf('ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN')
    expect(arg).toBeGreaterThan(-1)
    expect(env).toBeGreaterThan(arg)
    expect(buildAt).toBeGreaterThan(env)
  })

  it('builds on a supported Node major (22 or later)', () => {
    const major = Number(dockerfile.match(/^FROM node:(\d+)/m)?.[1])
    expect(major).toBeGreaterThanOrEqual(22)
  })
})

describe('frontend/Caddyfile CSP connect-src', () => {
  const connect = cspDirective('connect-src')

  it('allows Sentry ingest hosts for US, EU and older DSNs', () => {
    expect(allows(connect, 'https://o4507000000000000.ingest.us.sentry.io/api/1/envelope/')).toBe(true)
    expect(allows(connect, 'https://o4507000000000000.ingest.de.sentry.io/api/1/envelope/')).toBe(true)
    expect(allows(connect, 'https://o123456.ingest.sentry.io/api/1/envelope/')).toBe(true)
  })

  it('still allows Clerk and the backend origin (Critical Gotcha 5)', () => {
    expect(allows(connect, 'https://clerk.myide.ai/v1/client')).toBe(true)
    expect(allows(connect, 'https://backend-production-9c212.up.railway.app/api/v1/auth/me')).toBe(true)
  })

  it('positive control: the matcher rejects a host the policy does not list', () => {
    expect(allows(connect, 'https://sentry.io/api/1/envelope/')).toBe(false)
    expect(allows(connect, 'https://evil.example/collect')).toBe(false)
  })
})
