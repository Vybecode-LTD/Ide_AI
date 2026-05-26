import { renderToString } from 'react-dom/server'
import { StaticRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import type { HelmetServerState } from 'react-helmet-async'
import { Landing } from './pages/Landing'

export function render(url: string): { html: string; helmetContext: { helmet?: HelmetServerState } } {
  const helmetContext: { helmet?: HelmetServerState } = {}
  const html = renderToString(
    <HelmetProvider context={helmetContext}>
      <StaticRouter location={url}>
        <Landing />
      </StaticRouter>
    </HelmetProvider>
  )
  return { html, helmetContext }
}
