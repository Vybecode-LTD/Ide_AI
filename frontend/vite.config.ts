/// <reference types="vitest/config" />
/**
 * vite.config.ts — Vite configuration for Ide/AI frontend.
 * Uses @tailwindcss/vite plugin and proxies /api to the FastAPI backend.
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true }
    }
  },
  ssr: {
    // Bundle ESM-only packages so the SSR prerender script can import them in Node.js
    noExternal: ['framer-motion', 'react-helmet-async'],
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
