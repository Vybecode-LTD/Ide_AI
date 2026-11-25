import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

vi.mock('../lib/errorTracking', () => ({ reportError: vi.fn() }))

import { reportError } from '../lib/errorTracking'
import { ErrorBoundary } from '../components/ui/ErrorBoundary'

function Broken(): never {
  throw new Error('render failed')
}

describe('ErrorBoundary', () => {
  it('reports a render error with its component stack and shows the recovery screen', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(reportError).toHaveBeenCalledTimes(1)
    const [error, extra] = vi.mocked(reportError).mock.calls[0]
    expect((error as Error).message).toBe('render failed')
    expect(extra).toEqual({ componentStack: expect.stringContaining('Broken') })
    consoleError.mockRestore()
  })
})
