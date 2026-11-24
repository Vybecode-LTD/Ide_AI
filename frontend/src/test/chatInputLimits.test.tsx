/**
 * Chat inputs — a message over the server's cap is never sent.
 *
 * Finding C-3 (part): the server now rejects a chat message or module answer
 * longer than CHAT_MESSAGE_MAX_CHARS with a 422. Both pages must say so before
 * sending, disable Send, and not post on Enter. Exactly the cap still sends.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import type { ReactNode } from 'react'
import apiClient from '../lib/apiClient'
import { CHAT_MESSAGE_MAX_CHARS } from '../lib/inputLimits'
import { Discovery } from '../pages/Discovery'
import { ModuleSession } from '../pages/ModuleSession'

const { send } = vi.hoisted(() => ({ send: vi.fn() }))

vi.mock('../hooks/useSSE', () => ({
  useSSE: () => ({ send, abort: vi.fn(), isStreaming: false }),
}))
vi.mock('../lib/apiClient', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
  getAuthToken: vi.fn(),
}))
vi.mock('react-hot-toast', () => ({ default: { error: vi.fn(), success: vi.fn() } }))
vi.mock('../components/layout/Sidebar', () => ({ Sidebar: () => null }))
vi.mock('../components/layout/TopBar', () => ({ TopBar: () => null }))
vi.mock('../components/tutorial', () => ({
  StageInterlude: () => null,
  PulseBeacon: ({ children }: { children: ReactNode }) => <>{children}</>,
  Whisper: ({ children }: { children: ReactNode }) => <>{children}</>,
}))
vi.mock('../components/pathway/PathwayProgress', () => ({ PathwayProgress: () => null }))
vi.mock('../components/discovery/QuickChips', () => ({ QuickChips: () => null }))
vi.mock('../components/discovery/ChatThread', () => ({ ChatThread: () => null }))
vi.mock('../components/discovery/StagesStepper', () => ({ StagesStepper: () => null }))
vi.mock('../components/discovery/TranscriptExportMenu', () => ({ TranscriptExportMenu: () => null }))
vi.mock('../components/discovery/ProgressPanel', () => ({ ProgressPanel: () => null }))
vi.mock('../components/framework/DesignSheetPanel', () => ({ DesignSheetPanel: () => null }))
vi.mock('../components/partner/ActivePartnerBadge', () => ({ ActivePartnerBadge: () => null }))
vi.mock('../components/partner/PartnerSelector', () => ({ PartnerSelector: () => null }))
vi.mock('../components/voice/VoiceMicButton', () => ({ VoiceMicButton: () => null }))
vi.mock('../stores/modulePathwayStore', () => ({
  useModulePathwayStore: () => ({
    assembledModules: [],
    pathway: null,
    moduleResponses: {},
    fetchPathway: vi.fn().mockResolvedValue(undefined),
    fetchResponses: vi.fn().mockResolvedValue(undefined),
    setActiveModule: vi.fn(),
  }),
}))
vi.mock('../stores/pathwayStore', () => ({
  usePathwayStore: () => ({
    active: null,
    fetchPathways: vi.fn().mockResolvedValue(undefined),
    setActiveByProject: vi.fn(),
  }),
}))

// jsdom has no scrollTo; ModuleSession auto-scrolls its thread.
if (!Element.prototype.scrollTo) Element.prototype.scrollTo = () => {}

const get = vi.mocked(apiClient.get)
const post = vi.mocked(apiClient.post)

const OVER = 'Over the 4,000-character limit. Shorten it to continue.'
const atCap = 'x'.repeat(CHAT_MESSAGE_MAX_CHARS)
const overCap = 'x'.repeat(CHAT_MESSAGE_MAX_CHARS + 1)

beforeEach(() => {
  vi.clearAllMocks()
  get.mockResolvedValue({ data: {} })
})

function sentTo(pattern: RegExp) {
  return send.mock.calls.filter(([url]) => pattern.test(String(url)))
}

describe('ModuleSession answer input', () => {
  beforeEach(() => {
    post.mockResolvedValue({
      data: { label: 'Core problem', question: 'What hurts?', total_questions: 3 },
    })
  })

  async function renderPage() {
    render(
      <MemoryRouter initialEntries={['/modules/p1/core_problem']}>
        <Routes>
          <Route path="/modules/:projectId/:moduleId" element={<ModuleSession />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(post).toHaveBeenCalledWith('/modules/p1/core_problem/start'))
    return screen.getByLabelText('Your answer')
  }

  it('blocks an answer over the cap and says why', async () => {
    const input = await renderPage()
    fireEvent.change(input, { target: { value: overCap } })

    expect(screen.getByText(OVER)).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()

    fireEvent.keyDown(input, { key: 'Enter' })
    expect(sentTo(/\/respond$/)).toHaveLength(0)
  })

  it('sends an answer exactly at the cap', async () => {
    const input = await renderPage()
    fireEvent.change(input, { target: { value: atCap } })

    expect(screen.queryByText(OVER)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    const calls = sentTo(/\/modules\/p1\/core_problem\/respond$/)
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toEqual({ content: atCap })
  })
})

describe('Discovery message input', () => {
  beforeEach(() => {
    post.mockResolvedValue({
      data: { id: 's1', messages: [{ role: 'assistant', content: 'Hi' }], stage: 'problem' },
    })
  })

  async function renderPage() {
    render(
      <MemoryRouter initialEntries={['/discovery/p1']}>
        <Routes>
          <Route path="/discovery/:projectId" element={<Discovery />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(post).toHaveBeenCalledWith('/discovery/start', { project_id: 'p1' }))
    // The v1 sheet load runs after the session id is stored, so once it has
    // been requested a Send can go out.
    await waitFor(() => expect(get).toHaveBeenCalledWith('/discovery/s1/sheet'))
    return screen.getByLabelText('Enter your response to the AI partner')
  }

  it('blocks a message over the cap and says why', async () => {
    const input = await renderPage()
    fireEvent.change(input, { target: { value: overCap } })

    expect(screen.getByText(OVER)).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()

    fireEvent.keyDown(input, { key: 'Enter' })
    expect(sentTo(/\/message$/)).toHaveLength(0)
  })

  it('sends a message exactly at the cap', async () => {
    const input = await renderPage()
    fireEvent.change(input, { target: { value: atCap } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(sentTo(/\/discovery\/s1\/message$/)).toHaveLength(1))
    expect(sentTo(/\/message$/)[0][1]).toEqual({ content: atCap })
  })
})
