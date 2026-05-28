/**
 * inboxStore — Zustand store for the inbox unread count badge.
 *
 * Connects to a server-sent event stream at /inbox/stream (Redis pub/sub
 * backed) so the badge updates instantly when items arrive via email or
 * are added/promoted/deleted in another tab.
 *
 * Falls back gracefully when the stream isn't available (e.g. local dev
 * without Redis, or backend without REDIS_URL set) — caller can still
 * invoke refresh() / adjust() to keep the count in sync.
 *
 * @module stores/inboxStore
 */
import { create } from 'zustand'
import apiClient, { getAuthToken } from '../lib/apiClient'

interface InboxState {
  count: number
  /** True while an SSE connection is open. */
  streamConnected: boolean
  /** Fetch the latest count from the server. Silent on failure. */
  refresh: () => Promise<void>
  /** Apply an optimistic delta (e.g. -1 after delete). Clamped at 0. */
  adjust: (delta: number) => void
  /** Open the realtime stream. Idempotent — safe to call repeatedly. */
  connectStream: () => Promise<void>
  /** Close the realtime stream and cancel any pending reconnect. */
  disconnectStream: () => void
}

// ── Module-level stream state ─────────────────────────────────────
// These live outside the Zustand store because they're mutable refs
// to the in-flight fetch + reconnect timer. They are *not* part of
// component state and should not trigger re-renders when mutated.
let _abortController: AbortController | null = null
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null
let _reconnectAttempts = 0
let _giveUp = false  // Set when the server tells us realtime isn't available (503)

function _clearReconnect() {
  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer)
    _reconnectTimer = null
  }
}

function _backoffDelayMs(attempt: number): number {
  // 1s, 2s, 4s, 8s, 16s, capped at 30s
  return Math.min(30_000, 1_000 * Math.pow(2, attempt - 1))
}

/** Parse a single SSE event block ('event: x\ndata: y') into { event, data }. */
function _parseEvent(block: string): { event: string; data: string } | null {
  let event = 'message'
  let data = ''
  for (const line of block.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7).trim()
    else if (line.startsWith('data: ')) data = line.slice(6)
  }
  return data ? { event, data } : null
}

export const useInboxStore = create<InboxState>((set, get) => ({
  count: 0,
  streamConnected: false,

  refresh: async () => {
    try {
      const { data } = await apiClient.get<{ count: number }>('/inbox/count')
      set({ count: data?.count ?? 0 })
    } catch {
      // Silent — keep previous count
    }
  },

  adjust: (delta) =>
    set((s) => ({ count: Math.max(0, s.count + delta) })),

  connectStream: async () => {
    if (_giveUp) return  // Server said no realtime — don't keep trying

    // Cancel any in-flight connection / pending reconnect
    _abortController?.abort()
    _clearReconnect()
    _abortController = new AbortController()
    const signal = _abortController.signal

    let scheduleReconnect = true

    try {
      const token = await getAuthToken()
      if (!token) {
        throw new Error('Auth token not ready')
      }

      const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
      const response = await fetch(`${baseUrl}/inbox/stream`, {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      })

      if (response.status === 503) {
        // Realtime not configured — fall back to whatever caller does
        _giveUp = true
        scheduleReconnect = false
        return
      }

      if (!response.ok || !response.body) {
        // Other failure (401, 5xx) — reconnect with backoff
        throw new Error(`HTTP ${response.status}`)
      }

      _reconnectAttempts = 0  // Connection established
      set({ streamConnected: true })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // SSE events are \n\n-separated blocks
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() || ''

        for (const block of blocks) {
          const parsed = _parseEvent(block)
          if (!parsed) continue
          try {
            const payload = JSON.parse(parsed.data)
            if (parsed.event === 'hello' && typeof payload.count === 'number') {
              set({ count: payload.count })
            } else if (parsed.event === 'update') {
              // The payload type (added/promoted/deleted) could drive optimistic
              // adjust here, but a refresh is simpler and avoids race conditions
              // with same-tab adjust() calls (e.g. Inbox.tsx delete + SSE delivery)
              await get().refresh()
            }
          } catch {
            // skip malformed event
          }
        }
      }
    } catch (err) {
      const e = err as { name?: string }
      if (e?.name === 'AbortError') {
        scheduleReconnect = false
      }
    } finally {
      set({ streamConnected: false })
      if (scheduleReconnect && !_giveUp) {
        _reconnectAttempts += 1
        const delay = _backoffDelayMs(_reconnectAttempts)
        _reconnectTimer = setTimeout(() => {
          _reconnectTimer = null
          get().connectStream().catch(() => {})
        }, delay)
      }
    }
  },

  disconnectStream: () => {
    _abortController?.abort()
    _abortController = null
    _clearReconnect()
    _reconnectAttempts = 0
    _giveUp = false  // Reset so a fresh mount (e.g. after re-login) can retry
    set({ streamConnected: false })
  },
}))
