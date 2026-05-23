/**
 * adminStore — Zustand store for the /admin user-management page.
 * Holds the user list (paginated, searchable), per-user detail, and
 * the audit log list. All mutations refresh the affected detail.
 * @module stores/adminStore
 */
import { create } from 'zustand'
import apiClient from '../lib/apiClient'

export interface AdminUserListItem {
  id: string
  email: string
  name: string | null
  display_name: string | null
  avatar_url: string | null
  account_type: string
  is_admin: boolean
  entitlement_overrides: Record<string, number | null> | null
  stripe_customer_id: string | null
  project_count: number
  created_at: string
  updated_at: string
}

export interface AdminUserDetail extends AdminUserListItem {
  bio: string | null
  inbox_email: string | null
  email_verified: boolean
  oauth_provider: string | null
  clerk_user_id: string | null
  market_analysis_count: number
  sprint_plan_count: number
  prompt_kit_count: number
  effective_limits: Record<string, number | null>
}

export interface AdminAuditLogItem {
  id: string
  admin_user_id: string | null
  admin_email: string | null
  action: string
  target_user_id: string | null
  target_email: string | null
  details: Record<string, unknown> | null
  created_at: string
}

interface PaginatedUsers {
  items: AdminUserListItem[]
  total: number
  page: number
  per_page: number
}

interface PaginatedAudit {
  items: AdminAuditLogItem[]
  total: number
  page: number
  per_page: number
}

interface AdminState {
  // List
  users: PaginatedUsers
  usersLoading: boolean
  search: string
  planFilter: string // '' | 'free' | 'basic' | 'pro'

  // Detail
  selectedUser: AdminUserDetail | null
  detailLoading: boolean

  // Audit
  audit: PaginatedAudit
  auditLoading: boolean

  // Actions
  fetchUsers: (page?: number) => Promise<void>
  setSearch: (s: string) => void
  setPlanFilter: (p: string) => void
  fetchUserDetail: (userId: string) => Promise<void>
  clearSelectedUser: () => void
  updatePlan: (userId: string, plan: string) => Promise<void>
  updateOverrides: (userId: string, overrides: Record<string, number | null> | null) => Promise<void>
  setAdminFlag: (userId: string, isAdmin: boolean) => Promise<void>
  fetchAudit: (page?: number) => Promise<void>
}

const EMPTY_USERS: PaginatedUsers = { items: [], total: 0, page: 1, per_page: 50 }
const EMPTY_AUDIT: PaginatedAudit = { items: [], total: 0, page: 1, per_page: 50 }

export const useAdminStore = create<AdminState>((set, get) => ({
  users: EMPTY_USERS,
  usersLoading: false,
  search: '',
  planFilter: '',
  selectedUser: null,
  detailLoading: false,
  audit: EMPTY_AUDIT,
  auditLoading: false,

  fetchUsers: async (page) => {
    const { search, planFilter, users } = get()
    set({ usersLoading: true })
    try {
      const params: Record<string, string | number> = {
        page: page ?? users.page,
        per_page: users.per_page,
      }
      if (search) params.search = search
      if (planFilter) params.plan = planFilter
      const { data } = await apiClient.get<PaginatedUsers>('/admin/users', { params })
      set({ users: data, usersLoading: false })
    } catch {
      set({ usersLoading: false })
    }
  },

  setSearch: (s) => set({ search: s }),
  setPlanFilter: (p) => set({ planFilter: p }),

  fetchUserDetail: async (userId) => {
    set({ detailLoading: true })
    try {
      const { data } = await apiClient.get<AdminUserDetail>(`/admin/users/${userId}`)
      set({ selectedUser: data, detailLoading: false })
    } catch {
      set({ detailLoading: false })
    }
  },

  clearSelectedUser: () => set({ selectedUser: null }),

  updatePlan: async (userId, plan) => {
    const { data } = await apiClient.patch<AdminUserDetail>(
      `/admin/users/${userId}/plan`,
      { account_type: plan },
    )
    set({ selectedUser: data })
    // Patch the row in the list as well
    set((state) => ({
      users: {
        ...state.users,
        items: state.users.items.map((u) =>
          u.id === userId ? { ...u, account_type: data.account_type } : u,
        ),
      },
    }))
  },

  updateOverrides: async (userId, overrides) => {
    const { data } = await apiClient.patch<AdminUserDetail>(
      `/admin/users/${userId}/overrides`,
      { entitlement_overrides: overrides },
    )
    set({ selectedUser: data })
    set((state) => ({
      users: {
        ...state.users,
        items: state.users.items.map((u) =>
          u.id === userId ? { ...u, entitlement_overrides: data.entitlement_overrides } : u,
        ),
      },
    }))
  },

  setAdminFlag: async (userId, isAdmin) => {
    const { data } = await apiClient.patch<AdminUserDetail>(
      `/admin/users/${userId}/admin`,
      { is_admin: isAdmin },
    )
    set({ selectedUser: data })
    set((state) => ({
      users: {
        ...state.users,
        items: state.users.items.map((u) =>
          u.id === userId ? { ...u, is_admin: data.is_admin } : u,
        ),
      },
    }))
  },

  fetchAudit: async (page) => {
    const { audit } = get()
    set({ auditLoading: true })
    try {
      const params = { page: page ?? audit.page, per_page: audit.per_page }
      const { data } = await apiClient.get<PaginatedAudit>('/admin/audit-log', { params })
      set({ audit: data, auditLoading: false })
    } catch {
      set({ auditLoading: false })
    }
  },
}))
