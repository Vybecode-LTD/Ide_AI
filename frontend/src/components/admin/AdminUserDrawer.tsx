/**
 * AdminUserDrawer — Slide-in panel with per-user admin actions.
 * Lets admins change plan, edit entitlement overrides, and toggle admin flag.
 * @module components/admin/AdminUserDrawer
 */
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Button } from '../ui/Button'
import { useAdminStore } from '../../stores/adminStore'
import { useAuthStore } from '../../stores/authStore'
import { extractError } from '../../lib/extractError'

interface Props {
  userId: string | null
  onClose: () => void
}

const PLANS = ['free', 'basic', 'pro']
const LIMIT_KEYS: Array<{ key: string; label: string }> = [
  { key: 'projects', label: 'Projects' },
  { key: 'prompt_packages', label: 'Prompt Kits' },
  { key: 'market_analysis', label: 'Market Analyses' },
  { key: 'sprint_plans', label: 'Sprint Plans' },
]

type OverrideMode = 'inherit' | 'unlimited' | 'custom'

interface OverrideRow {
  mode: OverrideMode
  customValue: string
}

function deriveRows(
  overrides: Record<string, number | null> | null | undefined,
): Record<string, OverrideRow> {
  const rows: Record<string, OverrideRow> = {}
  for (const { key } of LIMIT_KEYS) {
    if (overrides && key in overrides) {
      const v = overrides[key]
      rows[key] = v === null
        ? { mode: 'unlimited', customValue: '' }
        : { mode: 'custom', customValue: String(v) }
    } else {
      rows[key] = { mode: 'inherit', customValue: '' }
    }
  }
  return rows
}

function rowsToPayload(rows: Record<string, OverrideRow>): Record<string, number | null> | null {
  const out: Record<string, number | null> = {}
  for (const { key } of LIMIT_KEYS) {
    const r = rows[key]
    if (r.mode === 'inherit') continue
    if (r.mode === 'unlimited') out[key] = null
    if (r.mode === 'custom') {
      const n = Number(r.customValue)
      if (!Number.isFinite(n) || n < 0) continue // invalid → skip
      out[key] = n
    }
  }
  return Object.keys(out).length > 0 ? out : null
}

export function AdminUserDrawer({ userId, onClose }: Props) {
  const {
    selectedUser,
    detailLoading,
    fetchUserDetail,
    updatePlan,
    updateOverrides,
    setAdminFlag,
  } = useAdminStore()
  const currentAuthUser = useAuthStore((s) => s.user)

  const [overrideRows, setOverrideRows] = useState<Record<string, OverrideRow>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (userId) {
      fetchUserDetail(userId)
    }
  }, [userId, fetchUserDetail])

  useEffect(() => {
    if (selectedUser) {
      setOverrideRows(deriveRows(selectedUser.entitlement_overrides))
    }
  }, [selectedUser])

  // Close on Escape
  useEffect(() => {
    if (!userId) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [userId, onClose])

  if (!userId) return null

  const handlePlanChange = async (plan: string) => {
    if (!selectedUser || plan === selectedUser.account_type) return
    setSaving(true)
    try {
      await updatePlan(selectedUser.id, plan)
      toast.success(`Plan updated to ${plan}.`)
    } catch (err) {
      toast.error(extractError(err, "Couldn't update plan."))
    } finally {
      setSaving(false)
    }
  }

  const handleSaveOverrides = async () => {
    if (!selectedUser) return
    const payload = rowsToPayload(overrideRows)
    setSaving(true)
    try {
      await updateOverrides(selectedUser.id, payload)
      toast.success('Overrides saved.')
    } catch (err) {
      toast.error(extractError(err, "Couldn't save overrides."))
    } finally {
      setSaving(false)
    }
  }

  const handleAdminToggle = async () => {
    if (!selectedUser) return
    const next = !selectedUser.is_admin
    setSaving(true)
    try {
      await setAdminFlag(selectedUser.id, next)
      toast.success(next ? 'Granted admin.' : 'Revoked admin.')
    } catch (err) {
      toast.error(extractError(err, "Couldn't change admin status."))
    } finally {
      setSaving(false)
    }
  }

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
    })

  const isSelf = selectedUser?.id === currentAuthUser?.id

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <aside
        className="fixed right-0 top-0 bottom-0 z-50 w-full md:w-[480px] bg-surface border-l border-border overflow-y-auto"
        role="dialog"
        aria-labelledby="admin-drawer-title"
        aria-modal="true"
      >
        {/* Header */}
        <div className="sticky top-0 bg-surface border-b border-border px-5 py-3 flex items-center justify-between z-10">
          <h2 id="admin-drawer-title" className="text-base font-semibold text-white">User Detail</h2>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-white text-lg leading-none"
            aria-label="Close drawer"
          >
            ×
          </button>
        </div>

        {detailLoading || !selectedUser ? (
          <div className="px-5 py-8 text-center text-text-muted text-sm">Loading...</div>
        ) : (
          <div className="px-5 py-5 space-y-6">
            {/* Identity */}
            <section>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 rounded-full bg-accent/20 border-2 border-accent/30 flex items-center justify-center text-lg text-accent font-bold overflow-hidden">
                  {selectedUser.avatar_url ? (
                    <img src={selectedUser.avatar_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    (selectedUser.display_name || selectedUser.name || selectedUser.email).charAt(0).toUpperCase()
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-white truncate">
                    {selectedUser.display_name || selectedUser.name || selectedUser.email}
                  </p>
                  <p className="text-xs text-text-muted truncate">{selectedUser.email}</p>
                </div>
              </div>
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                <dt className="text-text-muted">Joined</dt>
                <dd className="text-white">{formatDate(selectedUser.created_at)}</dd>
                <dt className="text-text-muted">Stripe</dt>
                <dd className="text-white font-mono text-[10px] truncate">
                  {selectedUser.stripe_customer_id || '—'}
                </dd>
                <dt className="text-text-muted">Clerk ID</dt>
                <dd className="text-white font-mono text-[10px] truncate">
                  {selectedUser.clerk_user_id || '—'}
                </dd>
                <dt className="text-text-muted">OAuth</dt>
                <dd className="text-white">{selectedUser.oauth_provider || '—'}</dd>
              </dl>
            </section>

            {/* Plan */}
            <section>
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Plan</h3>
              <div className="flex gap-2">
                {PLANS.map((p) => (
                  <button
                    key={p}
                    onClick={() => handlePlanChange(p)}
                    disabled={saving}
                    className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium border transition-colors capitalize ${
                      selectedUser.account_type === p
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border bg-white/5 text-text-muted hover:text-white'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </section>

            {/* Usage */}
            <section>
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Usage</h3>
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                <dt className="text-text-muted">Projects</dt>
                <dd className="text-white">{selectedUser.project_count}</dd>
                <dt className="text-text-muted">Prompt Kits</dt>
                <dd className="text-white">{selectedUser.prompt_kit_count}</dd>
                <dt className="text-text-muted">Market Analyses</dt>
                <dd className="text-white">{selectedUser.market_analysis_count}</dd>
                <dt className="text-text-muted">Sprint Plans</dt>
                <dd className="text-white">{selectedUser.sprint_plan_count}</dd>
              </dl>
            </section>

            {/* Overrides */}
            <section>
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1">
                Entitlement Overrides
              </h3>
              <p className="text-[11px] text-text-muted mb-3">
                Per-user limits that win over plan defaults. "Inherit" falls back to the plan.
                "Unlimited" sets no cap.
              </p>
              <div className="space-y-2">
                {LIMIT_KEYS.map(({ key, label }) => {
                  const row = overrideRows[key] || { mode: 'inherit', customValue: '' }
                  const effective = selectedUser.effective_limits[key]
                  return (
                    <div key={key} className="grid grid-cols-[1fr_110px_90px] gap-2 items-center">
                      <div>
                        <p className="text-xs text-white">{label}</p>
                        <p className="text-[10px] text-text-muted">
                          Effective: {effective === null ? 'unlimited' : effective}
                        </p>
                      </div>
                      <select
                        value={row.mode}
                        onChange={(e) =>
                          setOverrideRows((prev) => ({
                            ...prev,
                            [key]: { ...row, mode: e.target.value as OverrideMode },
                          }))
                        }
                        className="bg-white/5 border border-border rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-accent transition-colors"
                      >
                        <option value="inherit">Inherit</option>
                        <option value="unlimited">Unlimited</option>
                        <option value="custom">Custom</option>
                      </select>
                      <input
                        type="number"
                        min={0}
                        value={row.customValue}
                        onChange={(e) =>
                          setOverrideRows((prev) => ({
                            ...prev,
                            [key]: { ...row, customValue: e.target.value },
                          }))
                        }
                        disabled={row.mode !== 'custom'}
                        placeholder="—"
                        className="bg-white/5 border border-border rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-accent transition-colors disabled:opacity-40"
                      />
                    </div>
                  )
                })}
              </div>
              <div className="flex justify-end mt-3">
                <Button size="sm" onClick={handleSaveOverrides} disabled={saving}>
                  {saving ? 'Saving...' : 'Save Overrides'}
                </Button>
              </div>
            </section>

            {/* Admin toggle */}
            <section>
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                Admin Access
              </h3>
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-border">
                <div>
                  <p className="text-xs text-white">
                    {selectedUser.is_admin ? 'Is admin' : 'Not admin'}
                  </p>
                  <p className="text-[10px] text-text-muted">
                    {isSelf
                      ? 'You cannot revoke your own admin status.'
                      : 'Admins have full access to /admin and audit log.'}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant={selectedUser.is_admin ? 'ghost' : 'primary'}
                  onClick={handleAdminToggle}
                  disabled={saving || (isSelf && selectedUser.is_admin)}
                >
                  {selectedUser.is_admin ? 'Revoke' : 'Grant'}
                </Button>
              </div>
            </section>
          </div>
        )}
      </aside>
    </>
  )
}
