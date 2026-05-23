/**
 * AdminUserTable — Paginated user list with search + plan filter.
 * Click a row to open the user detail drawer.
 * @module components/admin/AdminUserTable
 */
import { useEffect } from 'react'
import { useAdminStore } from '../../stores/adminStore'

interface Props {
  onSelectUser: (userId: string) => void
}

const PLAN_BADGE: Record<string, string> = {
  free: 'bg-white/5 text-text-muted',
  basic: 'bg-blue-500/10 text-blue-400',
  pro: 'bg-accent/15 text-accent',
}

export function AdminUserTable({ onSelectUser }: Props) {
  const {
    users,
    usersLoading,
    search,
    planFilter,
    setSearch,
    setPlanFilter,
    fetchUsers,
  } = useAdminStore()

  // Initial load + refetch when filters change (debounced search)
  useEffect(() => {
    const t = setTimeout(() => { fetchUsers(1) }, 200)
    return () => clearTimeout(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, planFilter])

  const totalPages = Math.max(1, Math.ceil(users.total / users.per_page))

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-3 mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by email, name, display name..."
          className="flex-1 bg-white/5 border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
        />
        <select
          value={planFilter}
          onChange={(e) => setPlanFilter(e.target.value)}
          className="bg-white/5 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent transition-colors"
        >
          <option value="">All plans</option>
          <option value="free">Free</option>
          <option value="basic">Basic</option>
          <option value="pro">Pro</option>
        </select>
        <span className="text-xs text-text-muted shrink-0">
          {users.total} user{users.total === 1 ? '' : 's'}
        </span>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border overflow-hidden">
        {/* Header */}
        <div className="hidden md:grid grid-cols-[1fr_120px_80px_80px_120px_60px] gap-2 px-4 py-2 bg-white/3 border-b border-border text-[10px] font-semibold text-text-muted uppercase tracking-wider">
          <span>User</span>
          <span>Plan</span>
          <span>Projects</span>
          <span>Override</span>
          <span>Joined</span>
          <span />
        </div>

        {/* Rows */}
        {usersLoading && users.items.length === 0 ? (
          <div className="px-4 py-12 text-center text-text-muted text-sm">Loading users...</div>
        ) : users.items.length === 0 ? (
          <div className="px-4 py-12 text-center text-text-muted text-sm">No users match.</div>
        ) : (
          users.items.map((u) => (
            <button
              key={u.id}
              onClick={() => onSelectUser(u.id)}
              className="w-full grid grid-cols-1 md:grid-cols-[1fr_120px_80px_80px_120px_60px] gap-1 md:gap-2 px-4 py-3 text-left border-b border-border last:border-b-0 hover:bg-white/3 transition-colors"
            >
              {/* User */}
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-7 h-7 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center text-[11px] text-accent font-bold shrink-0 overflow-hidden">
                  {u.avatar_url ? (
                    <img src={u.avatar_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    (u.display_name || u.name || u.email).charAt(0).toUpperCase()
                  )}
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-white truncate">
                    {u.display_name || u.name || u.email}
                    {u.is_admin && (
                      <span className="ml-1.5 text-[9px] text-accent uppercase">admin</span>
                    )}
                  </p>
                  <p className="text-[11px] text-text-muted truncate">{u.email}</p>
                </div>
              </div>
              {/* Plan */}
              <span className="md:self-center">
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${PLAN_BADGE[u.account_type] || PLAN_BADGE.free} capitalize`}>
                  {u.account_type}
                </span>
              </span>
              {/* Projects */}
              <span className="text-xs text-text-muted md:self-center">
                <span className="md:hidden text-[10px] text-text-muted/50 mr-1">Projects:</span>
                {u.project_count}
              </span>
              {/* Override */}
              <span className="text-xs md:self-center">
                {u.entitlement_overrides && Object.keys(u.entitlement_overrides).length > 0 ? (
                  <span className="text-amber-400">Yes</span>
                ) : (
                  <span className="text-text-muted/50">—</span>
                )}
              </span>
              {/* Joined */}
              <span className="text-xs text-text-muted md:self-center">
                {formatDate(u.created_at)}
              </span>
              {/* Open icon */}
              <span className="text-accent text-xs md:self-center md:text-right">Open ›</span>
            </button>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={() => fetchUsers(users.page - 1)}
            disabled={users.page <= 1 || usersLoading}
            className="px-3 py-1.5 text-xs bg-white/5 border border-border rounded-lg text-text-muted hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            ‹ Prev
          </button>
          <span className="text-xs text-text-muted">
            Page {users.page} of {totalPages}
          </span>
          <button
            onClick={() => fetchUsers(users.page + 1)}
            disabled={users.page >= totalPages || usersLoading}
            className="px-3 py-1.5 text-xs bg-white/5 border border-border rounded-lg text-text-muted hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next ›
          </button>
        </div>
      )}
    </div>
  )
}
