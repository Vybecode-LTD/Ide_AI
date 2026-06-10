/**
 * main.tsx — Application entry point.
 * Wraps React with HelmetProvider, ClerkProvider, QueryClient, and Router providers.
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClerkProvider } from '@clerk/clerk-react'
import { dark } from '@clerk/themes'
import { HelmetProvider } from 'react-helmet-async'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import './styles/globals.css'
import App from './App'

const queryClient = new QueryClient()

// Error tracking — dynamic import so the Sentry bundle is only fetched when
// a DSN is configured (no-op + zero bundle cost otherwise).
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN
if (SENTRY_DSN) {
  import('@sentry/react').then((Sentry) => {
    Sentry.init({
      dsn: SENTRY_DSN,
      environment: import.meta.env.MODE,
      sendDefaultPii: false,
    })
  })
}

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY environment variable')
}

/** Clerk appearance — dark glassmorphism matching the Ide/AI design system. */
const clerkAppearance = {
  baseTheme: dark,
  variables: {
    colorPrimary: '#00E5FF',
    colorBackground: '#0d0d12',
    colorInputBackground: 'rgba(255,255,255,0.05)',
    colorText: '#ffffff',
    colorTextSecondary: '#888',
    borderRadius: '12px',
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  elements: {
    card: {
      backdropFilter: 'blur(20px)',
      background: 'rgba(13,13,18,0.9)',
      border: '1px solid rgba(0,229,255,0.1)',
      boxShadow: '0 0 40px rgba(0,229,255,0.05)',
    },
    formButtonPrimary: {
      background: '#00E5FF',
      color: '#0d0d12',
      fontWeight: '600',
    },
    formButtonPrimary__loading: {
      background: '#00E5FF',
      opacity: '0.7',
    },
    footerActionLink: {
      color: '#00E5FF',
    },
    identityPreviewEditButton: {
      color: '#00E5FF',
    },
  },
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <HelmetProvider>
        <ClerkProvider
          publishableKey={CLERK_PUBLISHABLE_KEY}
          appearance={clerkAppearance}
          afterSignOutUrl="/"
        >
          <QueryClientProvider client={queryClient}>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </QueryClientProvider>
        </ClerkProvider>
      </HelmetProvider>
    </ErrorBoundary>
  </StrictMode>
)
