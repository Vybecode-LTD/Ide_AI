import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSSE } from '../hooks/useSSE'

vi.mock('../lib/apiClient', () => ({
  getAuthToken: vi.fn().mockResolvedValue('mock-token'),
  default: { get: vi.fn(), post: vi.fn() },
}))

function makeSSEResponse(events: string[]): Response {
  const text = events.join('\n\n') + '\n\n'
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text))
      controller.close()
    },
  })
  return new Response(stream, { status: 200, headers: { 'content-type': 'text/event-stream' } })
}

describe('useSSE', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fires onToken for token events', async () => {
    const tokens: string[] = []
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      makeSSEResponse([
        'data: {"type":"token","content":"Hello"}',
        'data: {"type":"token","content":" world"}',
        'data: {"type":"done","stage":"greeting","chips":["a","b"]}',
      ]),
    )

    const { result } = renderHook(() =>
      useSSE({ onToken: (t) => tokens.push(t) }),
    )

    await act(async () => {
      await result.current.send('/api/v1/test', {})
    })

    expect(tokens).toEqual(['Hello', ' world'])
  })

  it('fires onDone with stage and chips', async () => {
    let doneData: { stage: string; chips: string[] } | null = null
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      makeSSEResponse([
        'data: {"type":"done","stage":"features","chips":["c1","c2","c3"]}',
      ]),
    )

    const { result } = renderHook(() =>
      useSSE({ onDone: (d) => { doneData = d } }),
    )

    await act(async () => {
      await result.current.send('/api/v1/test', {})
    })

    expect(doneData).toEqual({ stage: 'features', chips: ['c1', 'c2', 'c3'], complete: undefined, question_number: undefined })
  })

  it('fires safety-net onDone when stream ends without done event', async () => {
    let doneData: { stage: string; chips: string[] } | null = null
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      makeSSEResponse([
        'data: {"type":"token","content":"partial"}',
      ]),
    )

    const { result } = renderHook(() =>
      useSSE({ onDone: (d) => { doneData = d } }),
    )

    await act(async () => {
      await result.current.send('/api/v1/test', {})
    })

    expect(doneData).toEqual({ stage: '', chips: [] })
  })

  it('fires onFieldUpdate for field_update events', async () => {
    let payload: { updates: unknown[]; summary: unknown } | null = null
    const mockSummary = {
      total_filled: 3,
      total_fields: 10,
      required_filled: 2,
      required_total: 5,
      overall_percent: 30,
      per_module: [{ module_id: 'core', label: 'Core', filled: 2, total: 5, required_filled: 1, required_total: 3 }],
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      makeSSEResponse([
        `data: {"type":"field_update","updates":[{"module_id":"core","field_key":"name","value":"Test"}],"summary":${JSON.stringify(mockSummary)}}`,
        'data: {"type":"done","stage":"","chips":[]}',
      ]),
    )

    const { result } = renderHook(() =>
      useSSE({ onFieldUpdate: (p) => { payload = p } }),
    )

    await act(async () => {
      await result.current.send('/api/v1/test', {})
    })

    expect(payload).not.toBeNull()
    expect(payload!.updates).toHaveLength(1)
    expect(payload!.updates[0]).toEqual({ module_id: 'core', field_key: 'name', value: 'Test' })
    expect(payload!.summary).toEqual(mockSummary)
  })

  it('does not fire onFieldUpdate when summary is missing', async () => {
    let called = false
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      makeSSEResponse([
        'data: {"type":"field_update","updates":[{"module_id":"x","field_key":"y","value":"z"}]}',
        'data: {"type":"done","stage":"","chips":[]}',
      ]),
    )

    const { result } = renderHook(() =>
      useSSE({ onFieldUpdate: () => { called = true } }),
    )

    await act(async () => {
      await result.current.send('/api/v1/test', {})
    })

    expect(called).toBe(false)
  })

  it('fires onSheetUpdate for sheet_update events', async () => {
    let sheet: Record<string, unknown> | null = null
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      makeSSEResponse([
        'data: {"type":"sheet_update","sheet":{"problem":"Build a SaaS","audience":"devs"}}',
        'data: {"type":"done","stage":"","chips":[]}',
      ]),
    )

    const { result } = renderHook(() =>
      useSSE({ onSheetUpdate: (s) => { sheet = s } }),
    )

    await act(async () => {
      await result.current.send('/api/v1/test', {})
    })

    expect(sheet).toEqual({ problem: 'Build a SaaS', audience: 'devs' })
  })
})
