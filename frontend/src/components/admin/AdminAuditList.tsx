/**
 * AdminAuditList — Paginated table of admin actions, newest first.
 * @module components/admin/AdminAuditList
 */
import { useEffect } from 'react'
import { useAdminStore } from '../../stores/adminStore'

const ACTION_LABEL: Record<string, string> = {
  plan_changed: 'Plan changed',
  plan_unchanged: 'Plan no-op',
  overrides_updated: 'Overrides updated',
  admin_granted: 'Admin granted',
  admin_revoked: 'Admin revoked',
}

function formatDetail(action: string, details: Record<string, unknown> | null): string {
  if (!details) return ''
  if (action === 'plan_changed' && 'from' in details && 'to' in details) {
    return `${String(details.from)} → ${String(details.to)}`
  }
  if (action === 'overrides_updated') {
    const after = details.after as Record<string, unknown> | null | undefined
    if (after === null || after === undefined) return 'cleared'
    const keys = Object.keys(after)
    if (keys.length === 0) return 'cleared'
    return keys.map((k) => `${k}=${after[k] === null ? '∞' : after[k]}`).join(', ')
  }
  if (action.startsWith('admin_')) {
    return action === 'admin_granted' ? 'true' : 'false'
  }
  return ''
}

export function AdminAuditList() {
  const { audit, auditLoading, fetchAudit } = useAdminStore()

  useEffect(() => {
    fetchAudit(1)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const totalPages = Math.max(1, Math.ceil(audit.total / audit.per_page))

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
    })

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-text-muted">{audit.total} action{audit.total === 1 ? '' : 's'} logged</p>
        <button
          onClick={() => fetchAudit(audit.page)}
          disabled={auditLoading}
          className="text-xs text-text-muted hover:text-white transition-colors disabled:opacity-40"
        >
          Refresh
        </button>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <div className="hidden md:grid grid-cols-[160px_140px_1fr_1fr_1fr] gap-2 px-4 py-2 bg-white/3 border-b border-border text-[10px] font-semibold text-text-muted uppercase tracking-wider">
          <span>When</span>
          <span>Action</span>
          <span>Admin</span>
          <span>Target user</span>
          <span>Detail</span>
        </div>

        {auditLoading && audit.items.length === 0 ? (
          <div className="px-4 py-12 text-center text-text-muted text-sm">Loading...</div>
        ) : audit.items.length === 0 ? (
          <div className="px-4 py-12 text-center text-text-muted text-sm">No admin actions yet.</div>
        ) : (
          audit.items.map((entry) => (
            <div
              key={entry.id}
              className="grid grid-cols-1 md:grid-cols-[160px_140px_1fr_1fr_1fr] gap-1 md:gap-2 px-4 py-2 text-xs border-b border-border last:border-b-0 hover:bg-white/3 transition-colors"
            >
              <span className="text-text-muted">{formatTime(entry.created_at)}</span>
              <span className="text-accent">{ACTION_LABEL[entry.action] || entry.action}</span>
              <span className="text-white truncate">{entry.admin_email || '—'}</span>
              <span className="text-white truncate">{entry.target_email || '—'}</span>
              <span className="text-text-muted truncate font-mono text-[10px]">
                {formatDetail(entry.action, entry.details)}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={() => fetchAudit(audit.page - 1)}
            disabled={audit.page <= 1 || auditLoading}
            className="px-3 py-1.5 text-xs bg-white/5 border border-border rounded-lg text-text-muted hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            ‹ Prev
          </button>
          <span className="text-xs text-text-muted">
            Page {audit.page} of {totalPages}
          </span>
          <button
            onClick={() => fetchAudit(audit.page + 1)}
            disabled={audit.page >= totalPages || auditLoading}
            className="px-3 py-1.5 text-xs bg-white/5 border border-border rounded-lg text-text-muted hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next ›
          </button>
        </div>
      )}
    </div>
  )
}
