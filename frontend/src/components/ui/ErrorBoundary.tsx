/**
 * ErrorBoundary — Catches uncaught React errors and shows a recovery UI
 * instead of a blank/black screen.
 * @module components/ui/ErrorBoundary
 */
import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack)
    // Report to Sentry when configured (render errors never reach
    // window.onerror, so the boundary must capture them itself).
    if (import.meta.env.VITE_SENTRY_DSN) {
      import('@sentry/react').then((Sentry) =>
        Sentry.captureException(error, { extra: { componentStack: info.componentStack } })
      )
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-background flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl p-8 max-w-lg w-full text-center">
            <div className="text-4xl mb-4">⚠️</div>
            <h1 className="text-lg font-semibold text-white mb-2">Something went wrong</h1>
            <p className="text-sm text-text-muted mb-4">
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => this.setState({ hasError: false, error: null })}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-white/5 text-white border border-border hover:bg-white/10 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.href = '/'}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-accent text-background hover:bg-accent/90 transition-colors"
              >
                Go Home
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
