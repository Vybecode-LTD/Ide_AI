/**
 * authStore — Zustand store for user profile data from the backend.
 * Identity info (name, email, avatar) comes from Clerk's useUser() hook.
 * This store holds app-specific data: account_type, stripe info, preferences, bio.
 * @module stores/authStore
 */
import { create } from 'zustand'
import apiClient from '../lib/apiClient'

export interface AuthUser {
  id: string
  email: string
  name: string | null
  display_name: string | null
  avatar_url: string | null
  email_verified: boolean
  account_type: string
  is_admin: boolean
  bio: string | null
  inbox_email: string | null
  preferences: Record<string, unknown> | null
  created_at: string
}

interface AuthState {
  user: AuthUser | null
  loading: boolean
  /** Fetch /auth/me and populate user profile from backend. */
  fetchUser: () => Promise<AuthUser | null>
  /** Update local user state (after PATCH /auth/me or avatar upload). */
  setUser: (user: AuthUser) => void
  /** Clear user state. */
  logout: () => void
  /** Get initials for avatar fallback (first letter of name or email). */
  initials: () => string
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  loading: false,

  fetchUser: async () => {
    set({ loading: true })
    try {
      const { data } = await apiClient.get('/auth/me')
      set({ user: data, loading: false })
      return data
    } catch {
      set({ user: null, loading: false })
      return null
    }
  },

  setUser: (user) => set({ user }),

  logout: () => {
    set({ user: null })
  },

  initials: () => {
    const u = get().user
    if (!u) return '?'
    const source = u.display_name || u.name || u.email
    return source.charAt(0).toUpperCase()
  },
}))
