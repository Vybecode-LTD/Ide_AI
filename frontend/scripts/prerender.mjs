/**
 * prerender.mjs — Build-time SSR prerender for Ide/AI landing page.
 * Runs after `vite build` + `vite build --ssr`, injects React-rendered HTML and
 * react-helmet-async meta tags into dist/index.html for crawler visibility.
 * The SSR bundle in dist/server/ is deleted after use.
 */
import { readFileSync, writeFileSync, rmSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const toRoot = (p) => resolve(__dirname, '..', p)

console.log('🔍 Pre-rendering routes...')

const template = readFileSync(toRoot('dist/index.html'), 'utf-8')
// pathToFileURL → valid file:// URL on both Windows (C:\…) and Linux (/app/…);
// a raw absolute path throws ERR_UNSUPPORTED_ESM_URL_SCHEME on Windows.
const { render } = await import(pathToFileURL(toRoot('dist/server/entry-server.js')).href)

const routes = ['/']

for (const url of routes) {
  const { html: appHtml, helmetContext } = render(url)
  const h = helmetContext.helmet

  const headTags = h
    ? [h.title.toString(), h.meta.toString(), h.link.toString(), h.script.toString()]
        .filter(Boolean)
        .join('\n    ')
    : ''

  const rendered = template
    .replace('<!--app-head-->', headTags)
    .replace('<div id="root"></div>', `<div id="root">${appHtml}</div>`)

  const filePath = url === '/' ? toRoot('dist/index.html') : toRoot(`dist${url}.html`)
  writeFileSync(filePath, rendered)
  console.log(`✓ Pre-rendered: ${url}`)
}

// SSR bundle is only needed at build time — remove it so Caddy doesn't serve it
rmSync(toRoot('dist/server'), { recursive: true, force: true })
console.log('✓ SSR bundle cleaned up')
