/**
 * inboxStore — Zustand store for the inbox unread count badge.
 * Sidebar polls + subscribes. Inbox page calls `refresh()` after mutations
 * for instant badge updates instead of waiting for the 60s tick.
 * @module stores/inboxStore
 */
import { create } from 'zustand'
import apiClient from '../lib/apiClient'

interface InboxState {
  count: number
  /** Fetch the latest count from the server. Silent on failure. */
  refresh: () => Promise<void>
  /** Apply an optimistic delta (e.g. -1 after delete). Clamped at 0. */
  adjust: (delta: number) => void
}

export const useInboxStore = create<InboxState>((set) => ({
  count: 0,
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
}))
