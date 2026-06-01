/**
 * SharedProject — Public read-only view of a shared project.
 * Accessible without authentication via share token.
 * @module pages/SharedProject
 */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { FeedbackPanel } from '../components/sharing/FeedbackPanel'
import { PublicHeader } from '../components/layout/PublicHeader'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

interface SharedData {
  project: {
    name: string
    description: string | null
    platform: string
    audience: string
    complexity: string
    tone: string
  }
  design_sheet: {
    problem: string | null
    audience: string | null
    mvp: string | null
    features: unknown[]
    tone: string | null
    platform: string | null
    tech_constraints: string | null
    success_metric: string | null
    confidence_score: number
  } | null
  blocks: Array<{
    name: string
    description: string
    category: string
    priority: string
    effort: string
    is_mvp: boolean
  }>
  pipeline: Array<{ layer: string; tool: string }>
  market_analysis: {
    status: string | null
    target_market: unknown
    competitive_landscape: unknown
    market_metrics: unknown
    revenue_projections: unknown
    marketing_strategies: unknown
  } | null
  allow_feedback: boolean
  allow_ratings: boolean
  share_token: string
}

export function SharedProject() {
  const { token } = useParams<{ token: string }>()
  const [data, setData] = useState<SharedData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [needsPassword, setNeedsPassword] = useState(false)
  const [password, setPassword] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [shareAccessToken, setShareAccessToken] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    const fetchData = async () => {
      try {
        const resp = await fetch(`${API_BASE}/sharing/public/${token}`)
        const json = await resp.json()
        if (resp.status === 410) {
          setError('This share link has expired.')
        } else if (resp.status === 404) {
          setError('Share link not found.')
        } else if (json.requires_password) {
          setNeedsPassword(true)
        } else if (resp.ok) {
          setData(json)
        } else {
          setError(json.detail || 'Failed to load shared project.')
        }
      } catch {
        setError('Failed to connect to server.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [token])

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwError(null)
    try {
      const resp = await fetch(`${API_BASE}/sharing/public/${token}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      const json = await resp.json()
      if (resp.ok) {
        setData(json)
        if (json.share_access_token) setShareAccessToken(json.share_access_token)
        setNeedsPassword(false)
      } else {
        setPwError(json.detail || 'Incorrect password.')
      }
    } catch {
      setPwError('Failed to verify password.')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="text-4xl mb-4">:(</div>
          <h1 className="text-lg font-semibold text-white mb-2">Unavailable</h1>
          <p className="text-sm text-text-muted">{error}</p>
        </div>
      </div>
    )
  }

  if (needsPassword) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="bg-surface border border-border rounded-2xl p-8 max-w-md w-full">
          <h1 className="text-lg font-semibold text-white mb-2 text-center">Password Required</h1>
          <p className="text-sm text-text-muted mb-6 text-center">This project is password-protected.</p>
          <form onSubmit={handlePasswordSubmit}>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full bg-white/5 border border-border rounded-lg px-4 py-3 text-sm text-white placeholder-text-muted focus:outline-none focus:border-accent mb-4"
            />
            {pwError && <p className="text-red-400 text-xs mb-3">{pwError}</p>}
            <button
              type="submit"
              className="w-full bg-accent text-black font-medium py-2.5 rounded-lg text-sm hover:bg-accent/90 transition-colors"
            >
              View Project
            </button>
          </form>
        </div>
      </div>
    )
  }

  if (!data) return null

  const sheet = data.design_sheet
  const mvpBlocks = data.blocks.filter(b => b.is_mvp)
  const v2Blocks = data.blocks.filter(b => !b.is_mvp)

  return (
    <div className="min-h-screen bg-background">
      <PublicHeader />
      {/* Project header */}
      <div className="border-b border-border bg-surface/50">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-accent text-xl font-bold">Ide/AI</span>
            <span className="text-xs text-text-muted bg-white/5 px-2 py-0.5 rounded">Shared Project</span>
          </div>
          <h1 className="text-2xl font-bold text-white">{data.project.name}</h1>
          {data.project.description && (
            <p className="text-sm text-text-muted mt-1">{data.project.description}</p>
          )}
          <div className="flex gap-3 mt-3">
            {[data.project.platform, data.project.audience, data.project.complexity].filter(Boolean).map((tag, i) => (
              <span key={i} className="text-xs bg-white/5 border border-border rounded-full px-3 py-1 text-text-muted">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {/* Design Sheet */}
        {sheet && (
          <section>
            <h2 className="text-lg font-semibold text-white mb-4">Design Sheet</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sheet.problem && (
                <Card>
                  <div className="text-xs font-semibold text-accent uppercase mb-1">Problem</div>
                  <p className="text-sm text-text-muted">{sheet.problem}</p>
                </Card>
              )}
              {sheet.audience && (
                <Card>
                  <div className="text-xs font-semibold text-accent uppercase mb-1">Audience</div>
                  <p className="text-sm text-text-muted">{sheet.audience}</p>
                </Card>
              )}
              {sheet.mvp && (
                <Card className="md:col-span-2">
                  <div className="text-xs font-semibold text-accent uppercase mb-1">MVP Scope</div>
                  <p className="text-sm text-text-muted">{sheet.mvp}</p>
                </Card>
              )}
            </div>
          </section>
        )}

        {/* Blocks */}
        {data.blocks.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-white mb-4">
              Features <span className="text-text-muted text-sm font-normal">({data.blocks.length})</span>
            </h2>
            {mvpBlocks.length > 0 && (
              <>
                <h3 className="text-xs font-semibold text-accent uppercase mb-3">MVP</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
                  {mvpBlocks.map((b, i) => (
                    <Card key={i}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-semibold text-white">{b.name}</span>
                        <span className="text-[10px] bg-accent/15 text-accent px-1.5 py-0.5 rounded">{b.effort}</span>
                      </div>
                      <p className="text-xs text-text-muted">{b.description}</p>
                    </Card>
                  ))}
                </div>
              </>
            )}
            {v2Blocks.length > 0 && (
              <>
                <h3 className="text-xs font-semibold text-amber-400 uppercase mb-3">V2 / Future</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {v2Blocks.map((b, i) => (
                    <Card key={i}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-semibold text-white">{b.name}</span>
                        <span className="text-[10px] bg-amber-500/15 text-amber-400 px-1.5 py-0.5 rounded">{b.effort}</span>
                      </div>
                      <p className="text-xs text-text-muted">{b.description}</p>
                    </Card>
                  ))}
                </div>
              </>
            )}
          </section>
        )}

        {/* Pipeline */}
        {data.pipeline.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-white mb-4">Tech Stack</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {data.pipeline.map((p, i) => (
                <Card key={i}>
                  <div className="text-[10px] text-text-muted uppercase mb-1">{p.layer}</div>
                  <div className="text-sm font-medium text-white">{p.tool}</div>
                </Card>
              ))}
            </div>
          </section>
        )}

        {/* Feedback (comments + ratings) */}
        {(data.allow_feedback || data.allow_ratings) && (
          <FeedbackPanel
            shareToken={data.share_token}
            allowFeedback={data.allow_feedback}
            allowRatings={data.allow_ratings}
            shareAccessToken={shareAccessToken}
          />
        )}

        {/* Footer */}
        <div className="border-t border-border pt-6 text-center">
          <p className="text-xs text-text-muted">
            Built with <span className="text-accent font-medium">Ide/AI</span> — AI-powered product design
          </p>
        </div>
      </div>
    </div>
  )
}
