/**
 * ShareDialog — Modal for creating and managing public/private share links.
 * Supports password protection, link copying, and CSV export for Linear.
 * @module components/sharing/ShareDialog
 */
import { useState, useEffect } from 'react'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import apiClient from '../../lib/apiClient'

interface ShareDialogProps {
  projectId: string
  projectName: string
  open: boolean
  onClose: () => void
}

interface ShareData {
  share_token: string
  is_public: boolean
  has_password: boolean
  expires_at: string | null
  view_count: number
  share_url: string
  created_at: string
}

export function ShareDialog({ projectId, projectName, open, onClose }: ShareDialogProps) {
  const [shareData, setShareData] = useState<ShareData | null>(null)
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [copied, setCopied] = useState(false)
  const [revoking, setRevoking] = useState(false)

  // Create form state
  const [isPublic, setIsPublic] = useState(true)
  const [password, setPassword] = useState('')
  const [allowFeedback, setAllowFeedback] = useState(true)
  const [allowRatings, setAllowRatings] = useState(true)

  // Fetch existing share status
  useEffect(() => {
    if (open && projectId) {
      fetchShareStatus()
    }
  }, [open, projectId])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  const fetchShareStatus = async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get(`/sharing/${projectId}/status`)
      if (data.active) {
        setShareData(data)
      } else {
        setShareData(null)
      }
    } catch {
      // No existing share — that's fine
      setShareData(null)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    setCreating(true)
    try {
      const { data } = await apiClient.post(`/sharing/${projectId}`, {
        is_public: isPublic,
        allow_feedback: allowFeedback,
        allow_ratings: allowRatings,
        ...(password.trim() ? { password: password.trim() } : {}),
      })
      setShareData(data)
      setPassword('')
    } catch (err) {
      console.error('Failed to create share link:', err)
    } finally {
      setCreating(false)
    }
  }

  const handleCopy = async () => {
    if (!shareData) return
    const url = `${window.location.origin}/shared/${shareData.share_token}`
    await navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRevoke = async () => {
    setRevoking(true)
    try {
      await apiClient.delete(`/sharing/${projectId}`)
      setShareData(null)
    } catch (err) {
      console.error('Failed to revoke share link:', err)
    } finally {
      setRevoking(false)
    }
  }

  const handleExportCSV = async () => {
    if (!shareData) return
    try {
      const response = await apiClient.get(
        `/sharing/public/${shareData.share_token}/csv`,
        { responseType: 'blob' }
      )
      const slug = projectName.toLowerCase().replace(/\s+/g, '-').slice(0, 30)
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `${slug}-blocks.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('CSV export failed:', err)
    }
  }

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4" role="dialog" aria-labelledby="share-dialog-title" aria-modal="true">
        <Card glow className="w-full max-w-md relative">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h2 id="share-dialog-title" className="text-base font-semibold text-white">Share Project</h2>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-white transition-colors text-lg"
            >
              ✕
            </button>
          </div>

          {loading ? (
            <div className="py-8 text-center text-text-muted text-sm">Loading...</div>
          ) : shareData ? (
            /* ── Active share link ── */
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-green-400 text-sm">●</span>
                <span className="text-sm text-white font-medium">Share link active</span>
                {shareData.has_password && (
                  <span className="text-[10px] bg-amber-400/10 text-amber-400 px-1.5 py-0.5 rounded">
                    Password protected
                  </span>
                )}
              </div>

              {/* Share URL */}
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={`${window.location.origin}/shared/${shareData.share_token}`}
                  className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-xs text-text-muted font-mono truncate"
                />
                <Button size="sm" onClick={handleCopy}>
                  {copied ? 'Copied!' : 'Copy'}
                </Button>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-4 text-xs text-text-muted">
                <span>👁 {shareData.view_count} view{shareData.view_count !== 1 ? 's' : ''}</span>
                <span>Created {new Date(shareData.created_at).toLocaleDateString()}</span>
                {shareData.expires_at && (
                  <span>Expires {new Date(shareData.expires_at).toLocaleDateString()}</span>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 pt-2 border-t border-border">
                <Button variant="secondary" size="sm" onClick={handleExportCSV}>
                  Export CSV (Linear)
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRevoke}
                  disabled={revoking}
                  className="text-red-400 hover:text-red-300 ml-auto"
                >
                  {revoking ? 'Revoking...' : 'Revoke Link'}
                </Button>
              </div>
            </div>
          ) : (
            /* ── Create share form ── */
            <div className="space-y-4">
              <p className="text-sm text-text-muted">
                Create a read-only share link for <span className="text-white">{projectName}</span>.
                Anyone with the link can view the design kit.
              </p>

              {/* Visibility toggle */}
              <div>
                <label className="block text-xs font-medium text-text-muted mb-2">
                  Visibility
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsPublic(true)}
                    className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${
                      isPublic
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border bg-white/5 text-text-muted hover:text-white'
                    }`}
                  >
                    🌐 Public
                  </button>
                  <button
                    onClick={() => setIsPublic(false)}
                    className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${
                      !isPublic
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border bg-white/5 text-text-muted hover:text-white'
                    }`}
                  >
                    🔒 Password Protected
                  </button>
                </div>
              </div>

              {/* Password field */}
              {!isPublic && (
                <div>
                  <label className="block text-xs font-medium text-text-muted mb-1.5">
                    Password
                  </label>
                  <input
                    type="text"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter a password for viewers"
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
                  />
                </div>
              )}

              {/* Feedback toggles */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer">
                  <input
                    type="checkbox"
                    checked={allowFeedback}
                    onChange={(e) => setAllowFeedback(e.target.checked)}
                    className="accent-accent"
                  />
                  Allow viewer comments
                </label>
                <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer">
                  <input
                    type="checkbox"
                    checked={allowRatings}
                    onChange={(e) => setAllowRatings(e.target.checked)}
                    className="accent-accent"
                  />
                  Allow star ratings
                </label>
              </div>

              <Button
                className="w-full"
                onClick={handleCreate}
                disabled={creating || (!isPublic && !password.trim())}
              >
                {creating ? 'Creating...' : 'Create Share Link'}
              </Button>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
