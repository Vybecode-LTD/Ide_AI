/**
 * Exports page — errors on downloads.
 *
 * Downloads are requested with `responseType: 'blob'`, so an error body also
 * arrives as a Blob. The page used to parse it and hand `detail` straight to
 * the toast. For a plan-limit 403, `detail` is an object: React threw while
 * rendering the toast and the root error boundary replaced the whole app.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import type { ReactNode } from 'react'
import toast from 'react-hot-toast'
import apiClient from '../lib/apiClient'
import { Exports } from '../pages/Exports'

vi.mock('../lib/apiClient', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
vi.mock('react-hot-toast', () => ({ default: { error: vi.fn(), success: vi.fn() } }))
vi.mock('../components/layout/Sidebar', () => ({ Sidebar: () => null }))
vi.mock('../components/layout/TopBar', () => ({ TopBar: () => null }))
vi.mock('../components/tutorial', () => ({
  StageInterlude: () => null,
  Whisper: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

const post = vi.mocked(apiClient.post)
const get = vi.mocked(apiClient.get)
const toastError = vi.mocked(toast.error)

/** What axios rejects with when a `responseType: 'blob'` request fails. */
function blobError(status: number, body: string) {
  return { response: { status, data: new Blob([body], { type: 'application/json' }) } }
}

const LIMIT_DETAIL = {
  code: 'feature_limit_reached',
  feature: 'prompt_packages',
  current: 0,
  limit: 0,
  plan: 'free',
  message: 'Prompt Packages limit reached. Upgrade your plan.',
}

function renderExports() {
  return render(
    <MemoryRouter initialEntries={['/exports/p1']}>
      <Routes>
        <Route path="/exports/:projectId" element={<Exports />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Exports: prompt package errors', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens the upgrade dialog on a plan-limit 403 instead of toasting an object', async () => {
    post.mockRejectedValueOnce(blobError(403, JSON.stringify({ detail: LIMIT_DETAIL })))
    renderExports()

    fireEvent.click(screen.getByRole('button', { name: 'Generate & Download' }))

    expect(await screen.findByText('Feature Limit Reached')).toBeInTheDocument()
    expect(toastError).not.toHaveBeenCalled()
  })

  it("shows the server's message when detail is a string", async () => {
    post.mockRejectedValueOnce(
      blobError(400, JSON.stringify({ detail: 'Unsupported platform: foo.' })),
    )
    renderExports()

    fireEvent.click(screen.getByRole('button', { name: 'Generate & Download' }))

    await waitFor(() => expect(toastError).toHaveBeenCalledWith('Unsupported platform: foo.'))
  })

  it('never passes a non-string to the toast, whatever the body holds', async () => {
    post.mockRejectedValueOnce(blobError(502, '<html>Bad gateway</html>'))
    renderExports()

    fireEvent.click(screen.getByRole('button', { name: 'Generate & Download' }))

    await waitFor(() => expect(toastError).toHaveBeenCalledTimes(1))
    expect(typeof toastError.mock.calls[0][0]).toBe('string')
  })
})

describe('Exports: design kit download errors', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows the server's message from a blob error body", async () => {
    get.mockRejectedValueOnce(blobError(404, JSON.stringify({ detail: 'Project not found' })))
    renderExports()

    fireEvent.click(screen.getByRole('button', { name: /^Download/ }))

    await waitFor(() => expect(toastError).toHaveBeenCalledWith('Project not found'))
  })
})
