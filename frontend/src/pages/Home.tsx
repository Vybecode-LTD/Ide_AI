/**
 * Home -- Idea input landing page. Users first pick a category (CategorySelect),
 * then describe their idea, choose an AI partner, and start discovery.
 * @module pages/Home
 */
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '../components/ui/Button'
import { Sidebar } from '../components/layout/Sidebar'
import { IdeaNebulaCanvas } from '../components/nebula/IdeaNebulaCanvas'
import { TemplateGrid, type Template } from '../components/home/TemplateGrid'
import { CategorySelect } from './CategorySelect'
import type { PartnerStyleMeta } from '../types/project'
import apiClient from '../lib/apiClient'
import { extractError, getEntitlementDetail, type EntitlementDetail } from '../lib/extractError'
import { EntitlementLimitModal } from '../components/ui/EntitlementLimitModal'
import { useAuthStore } from '../stores/authStore'
import { PulseBeacon, Whisper } from '../components/tutorial'

/** Brief overlay shown after project creation while we fetch the assembled
 *  pathway and announce which modules will be filled during Discovery. */
interface ModulePreview {
  modules: Array<{ module_id: string; label: string; group: string }>
  totalRequired: number
}

/* ── Module-level cache for partner styles (never changes per session) ── */
let _partnerCache: PartnerStyleMeta[] | null = null

/* ── Page ─────────────────────────────────────────────────────── */
export function Home() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { user, initials, fetchUser } = useAuthStore()

  // Category from URL param — if missing, show CategorySelect screen
  const selectedCategory = searchParams.get('category')

  const [idea, setIdea] = useState('')

  // Billing success — initialize from URL param (avoids setState in effect).
  const [billingSuccess, setBillingSuccess] = useState(
    () => searchParams.get('billing') === 'success',
  )

  // Side effects for billing success: refresh user, clean URL, auto-dismiss.
  // Preserve ALL other params (e.g. `category`) when stripping `billing=success`
  // so a user landing on `/home?category=software&billing=success` doesn't lose
  // their category selection mid-flow.
  useEffect(() => {
    if (!billingSuccess) return
    fetchUser() // Refresh user to get updated account_type
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.delete('billing')
        return next
      },
      { replace: true },
    )
    const timer = setTimeout(() => setBillingSuccess(false), 5000)
    return () => clearTimeout(timer)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Track the post-create preview timeout so unmounting (manual nav, tab close)
  // can clear it before it fires a stale navigate().
  const previewTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    return () => {
      if (previewTimerRef.current) {
        clearTimeout(previewTimerRef.current)
        previewTimerRef.current = null
      }
    }
  }, [])
  const [loading, setLoading] = useState(false)
  const [upgradeDetail, setUpgradeDetail] = useState<EntitlementDetail | null>(null)
  const [createError, setCreateError] = useState('')
  const [modulePreview, setModulePreview] = useState<ModulePreview | null>(null)

  // Template state
  const [activeTemplate, setActiveTemplate] = useState<Template | null>(null)

  // AI Partner state
  const [partnerStyle, setPartnerStyle] = useState('strategist')
  const [allPartners, setAllPartners] = useState<PartnerStyleMeta[]>(() => _partnerCache ?? [])

  // ── Configuration selectors ────────────────────────────────────
  // Per CLAUDE.md spec: platform, audience, complexity, tone.
  const [platform, setPlatform] = useState<string>('custom')
  const [audience, setAudience] = useState<string>('consumers')
  const [complexity, setComplexity] = useState<string>('medium')
  const [tone, setTone] = useState<string>('casual')
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Display name from auth store (already fetched by Sidebar)
  const displayName = user?.display_name || user?.name || user?.email?.split('@')[0] || null

  // Fetch partner styles on mount
  useEffect(() => {
    if (_partnerCache) return
    apiClient.get('/meta/partner-styles')
      .then(({ data }) => { _partnerCache = data; setAllPartners(data) })
      .catch(() => {})
  }, [])

  /** Handle category selection from CategorySelect screen */
  const handleCategorySelect = (categoryId: string) => {
    setSearchParams({ category: categoryId }, { replace: true })
  }

  /** Fetch the assembled module pathway for a freshly-created project so we
   *  can show the user what they're about to fill out. Best-effort — falls
   *  back to immediate navigation if the pathway isn't queryable. */
  const showPreviewAndNavigate = async (projectId: string) => {
    try {
      const { data: pathway } = await apiClient.get(`/projects/${projectId}/pathway`)
      const modules = (pathway?.modules || []) as Array<string | { module_id: string; label?: string; group?: string }>
      if (modules.length === 0) {
        navigate(`/discovery/${projectId}`)
        return
      }
      // Normalize to {module_id, label, group}. Backend stores strings;
      // labels are looked up from a static map on the client.
      const decorated = modules.map((m) => {
        if (typeof m === 'string') {
          return { module_id: m, label: m.replace(/_/g, ' '), group: '' }
        }
        return {
          module_id: m.module_id,
          label: m.label || m.module_id.replace(/_/g, ' '),
          group: m.group || '',
        }
      })
      setModulePreview({ modules: decorated, totalRequired: decorated.length })
      // Auto-navigate after a short read of the preview. Stored in a ref so
      // the cleanup effect can cancel it if the component unmounts first
      // (manual sidebar nav, tab close) — otherwise the orphan timer fires
      // a navigate() that yanks the user away from wherever they went.
      if (previewTimerRef.current) clearTimeout(previewTimerRef.current)
      previewTimerRef.current = setTimeout(() => {
        previewTimerRef.current = null
        navigate(`/discovery/${projectId}`)
      }, 2200)
    } catch {
      // No pathway available (template project, v1 project, or assembly skipped)
      navigate(`/discovery/${projectId}`)
    }
  }

  /** Create the project and navigate to discovery. */
  const createProject = async () => {
    // If a template is active, use the template endpoint
    if (activeTemplate) {
      const { data } = await apiClient.post(`/templates/${activeTemplate.id}/use`, {
        extra_description: idea.trim() || undefined,
        ai_partner_style: partnerStyle,
      })
      // Templates currently bypass up-front assembly — go straight to Discovery
      navigate(`/discovery/${data.project_id}`)
      return
    }

    // Detect best pathway from the idea description; fall back to software_product.
    let pathwayId = 'software_product'
    try {
      const { data: detected } = await apiClient.post('/pathways/detect', {
        description: idea,
      })
      if (detected?.pathway_id) pathwayId = detected.pathway_id
    } catch {
      // Detection is best-effort — keep the default.
    }

    const { data } = await apiClient.post('/projects', {
      name: idea.slice(0, 100),
      description: idea,
      pathway_id: pathwayId,
      ai_partner_style: partnerStyle,
      primary_category: selectedCategory,
      platform,
      audience,
      complexity,
      tone,
    })
    // v2 projects: show the brief module preview before routing to Discovery
    // so the user sees what they're about to fill out. v1 projects (and any
    // case where the pathway isn't queryable) fall straight through.
    if (data?.flow_version === 'v2') {
      await showPreviewAndNavigate(data.id)
    } else {
      navigate(`/discovery/${data.id}`)
    }
  }

  /** Main submit handler — create project directly (category already chosen). */
  const handleSubmit = async () => {
    if (!idea.trim() && !activeTemplate) return
    setLoading(true)
    setCreateError('')
    try {
      await createProject()
    } catch (err) {
      const ent = getEntitlementDetail(err)
      if (ent) setUpgradeDetail(ent)
      else setCreateError(extractError(err, 'Failed to create project. Please try again.'))
      setLoading(false)
    }
  }

  // If no category selected, show the category picker
  if (!selectedCategory) {
    return (
      <div className="min-h-screen bg-background">
        <Sidebar />
        <div className="ml-0 md:ml-[232px]">
          <CategorySelect onSelect={handleCategorySelect} />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />

      {/* Mobile-only profile badge (top-right) */}
      {user && (
        <Link
          to="/profile"
          className="md:hidden fixed top-3 right-3 z-40 w-9 h-9 rounded-full bg-surface/80 backdrop-blur-sm border border-border flex items-center justify-center text-xs text-accent font-bold overflow-hidden shadow-lg"
          aria-label="Profile"
        >
          {user.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
          ) : (
            initials()
          )}
        </Link>
      )}

      {/* Billing success toast */}
      <AnimatePresence>
        {billingSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-green-500/20 border border-green-500/30 text-green-400 text-sm font-medium px-6 py-3 rounded-xl backdrop-blur-lg shadow-lg"
          >
            Subscription activated! Welcome to your new plan.
          </motion.div>
        )}
      </AnimatePresence>

      <main className="ml-0 md:ml-[232px] flex flex-col items-center justify-center min-h-screen px-4 md:px-6 pb-mobile-nav md:pb-0">
        <IdeaNebulaCanvas />

        {/* Greeting */}
        {displayName && (
          <motion.div
            className="text-center"
            style={{ paddingTop: 50 }}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-lg md:text-2xl font-semibold text-white/80">
              Hi <span className="text-accent">{displayName}</span>
            </h2>
          </motion.div>
        )}

        {/* Hero */}
        <motion.div
          className="text-center mb-8 md:mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <h1 className="text-2xl md:text-4xl font-bold text-white mb-3">
            Describe your <span className="text-accent">idea</span>
          </h1>
          <p className="text-text-muted text-sm md:text-lg">
            Tell us what you're building and we'll forge it into a complete design kit.
          </p>
        </motion.div>

        <motion.div
          className="w-full flex flex-col items-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {/* Idea textarea */}
          <Whisper id="home:idea" text="Describe your concept in a few sentences — the AI will take it from there">
          <div className="w-full max-w-2xl mb-6 md:mb-8">
            <div className="bg-surface border border-border rounded-xl focus-within:border-accent focus-within:ring-1 focus-within:ring-accent/30 transition-colors overflow-visible">
              {/* Active template pill */}
              {activeTemplate && (
                <div className="px-4 md:px-6 pt-3">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-orange-500/15 border border-orange-500/30 text-orange-300 text-sm font-medium">
                    <span>{activeTemplate.icon}</span>
                    <span>{activeTemplate.name}</span>
                    <button
                      type="button"
                      onClick={() => setActiveTemplate(null)}
                      className="ml-1 hover:text-white transition-colors"
                      title="Remove template"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                </div>
              )}
              <textarea
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                placeholder={activeTemplate
                  ? 'Add any additional idea detail (optional)...'
                  : 'Describe your idea in one sentence...'}
                className={`w-full bg-transparent px-4 md:px-6 pb-2 text-white text-base md:text-lg placeholder:text-text-muted focus:outline-none resize-none h-20 md:h-24 ${
                  activeTemplate ? 'pt-2' : 'pt-3 md:pt-4'
                }`}
              />
              {/* Category badge + change link */}
              <div className="px-4 md:px-6 pb-3 flex items-center gap-2">
                <span className="text-[10px] text-text-muted">Category:</span>
                <button
                  type="button"
                  onClick={() => setSearchParams({}, { replace: true })}
                  className="text-[10px] text-accent hover:text-accent/80 transition-colors"
                >
                  {selectedCategory.replace(/_/g, ' ')} &middot; change
                </button>
              </div>
            </div>
          </div>
          </Whisper>

          {/* AI Partner Style Selector */}
          {allPartners.length > 0 && (
            <PulseBeacon id="home:partners" position="top-right" className="w-full max-w-2xl">
            <div className="w-full max-w-2xl mb-4 md:mb-6">
              <label className="text-xs text-text-muted font-medium mb-3 block">
                Choose a partner style:
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {allPartners.map((p) => (
                  <div key={p.id} className="relative group">
                    <button
                      type="button"
                      onClick={() => setPartnerStyle(p.id)}
                      className={`
                        w-full flex flex-col items-center text-center rounded-lg px-2 py-2.5 cursor-pointer
                        transition-all duration-200 ease-out
                        ${
                          partnerStyle === p.id
                            ? 'bg-accent/5 border border-accent shadow-[0_0_16px_rgba(0,229,255,0.1)]'
                            : 'bg-white/5 border border-border hover:border-white/15 hover:scale-[1.02]'
                        }
                      `}
                    >
                      <span className="text-xl leading-none">{p.icon}</span>
                      <span className="text-[11px] font-semibold text-white mt-1.5">{p.name}</span>
                    </button>
                    {/* Tooltip */}
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg bg-surface border border-border shadow-xl text-[11px] text-text-muted leading-snug w-48 text-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-50 hidden sm:block">
                      <span className="font-semibold text-white">{p.name}</span>
                      <span className="block mt-0.5">{p.description}</span>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px w-2 h-2 bg-surface border-r border-b border-border rotate-45" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            </PulseBeacon>
          )}

          {/* Template grid — filtered to selected category. Placed directly
              below the partner picker per the v2 UX spec (templates inform
              what the user wants to build before they tweak advanced config). */}
          <TemplateGrid
            onSelect={(t) => setActiveTemplate(prev => prev?.id === t.id ? null : t)}
            selectedId={activeTemplate?.id}
            category={selectedCategory}
          />

          {/* Advanced configuration — collapsed by default */}
          <div className="w-full max-w-2xl mb-4 md:mb-6">
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="flex items-center gap-1.5 text-[11px] text-text-muted hover:text-accent transition-colors"
              aria-expanded={showAdvanced}
            >
              <span>{showAdvanced ? '▾' : '▸'}</span>
              <span>Advanced configuration</span>
              {!showAdvanced && (
                <span className="text-text-muted/60 ml-1">
                  ({platform} &middot; {audience} &middot; {complexity} &middot; {tone})
                </span>
              )}
            </button>

            <AnimatePresence>
              {showAdvanced && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 bg-white/5 border border-border rounded-xl p-4">
                    {/* Platform */}
                    <div>
                      <label className="text-[10px] text-text-muted font-medium block mb-1.5">
                        Platform
                      </label>
                      <select
                        value={platform}
                        onChange={(e) => setPlatform(e.target.value)}
                        className="w-full bg-background border border-border rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-accent transition-colors"
                      >
                        <option value="custom">Custom</option>
                        <option value="bubble">Bubble</option>
                        <option value="webflow">Webflow</option>
                        <option value="flutterflow">FlutterFlow</option>
                        <option value="bolt">Bolt</option>
                        <option value="lovable">Lovable</option>
                        <option value="claude_code">Claude Code</option>
                        <option value="cursor">Cursor</option>
                        <option value="replit">Replit</option>
                        <option value="n8n">n8n</option>
                      </select>
                    </div>

                    {/* Audience */}
                    <div>
                      <label className="text-[10px] text-text-muted font-medium block mb-1.5">
                        Audience
                      </label>
                      <select
                        value={audience}
                        onChange={(e) => setAudience(e.target.value)}
                        className="w-full bg-background border border-border rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-accent transition-colors"
                      >
                        <option value="consumers">Consumers</option>
                        <option value="businesses">Businesses</option>
                        <option value="internal_team">Internal Team</option>
                        <option value="developers">Developers</option>
                      </select>
                    </div>

                    {/* Complexity */}
                    <div>
                      <label className="text-[10px] text-text-muted font-medium block mb-1.5">
                        Complexity
                      </label>
                      <select
                        value={complexity}
                        onChange={(e) => setComplexity(e.target.value)}
                        className="w-full bg-background border border-border rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-accent transition-colors"
                      >
                        <option value="simple">Simple (1–5 screens)</option>
                        <option value="medium">Medium (5–15)</option>
                        <option value="complex">Complex (15+)</option>
                      </select>
                    </div>

                    {/* Tone */}
                    <div>
                      <label className="text-[10px] text-text-muted font-medium block mb-1.5">
                        Tone
                      </label>
                      <select
                        value={tone}
                        onChange={(e) => setTone(e.target.value)}
                        className="w-full bg-background border border-border rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-accent transition-colors"
                      >
                        <option value="formal">Formal</option>
                        <option value="casual">Casual</option>
                        <option value="technical">Technical</option>
                        <option value="startup">Startup-style</option>
                      </select>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Error display */}
          {createError && (
            <div className="text-red-400 text-xs bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-2 mb-3 max-w-md text-center">
              {createError}
            </div>
          )}

          {/* Submit */}
          <PulseBeacon id="home:start">
            <Button size="lg" onClick={handleSubmit} disabled={(!idea.trim() && !activeTemplate) || loading}>
              {loading ? 'Creating...' : 'Start Discovery \u2192'}
            </Button>
          </PulseBeacon>
        </motion.div>

      </main>

      {/* Module-preview overlay — shown after a v2 project is created, before
          we route to Discovery. Gives the user a 2-second read of which
          modules they're about to fill out. */}
      <AnimatePresence>
        {modulePreview && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-md flex items-center justify-center px-4"
            role="status"
            aria-live="polite"
          >
            <motion.div
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.3 }}
              className="bg-surface border border-accent/30 rounded-2xl shadow-[0_0_40px_rgba(0,229,255,0.15)] p-6 md:p-8 max-w-xl w-full"
            >
              <div className="text-center mb-5">
                <p className="text-xs uppercase tracking-wider text-accent font-semibold mb-1">
                  Design kit assembled
                </p>
                <h2 className="text-lg md:text-xl font-bold text-white">
                  {modulePreview.modules.length} modules to fill out
                </h2>
                <p className="text-xs text-text-muted mt-1">
                  Your AI partner will guide you through each one in Discovery.
                </p>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-1.5 max-h-60 overflow-y-auto pr-1">
                {modulePreview.modules.map((m, i) => (
                  <motion.div
                    key={m.module_id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.02, duration: 0.2 }}
                    className="text-[11px] text-white bg-white/5 border border-border rounded-md px-2.5 py-1.5 truncate capitalize"
                    title={m.label}
                  >
                    {m.label}
                  </motion.div>
                ))}
              </div>
              <div className="mt-5 flex items-center justify-center gap-2 text-[11px] text-text-muted">
                <span className="inline-block w-1.5 h-1.5 bg-accent rounded-full animate-pulse" />
                <span>Starting Discovery...</span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <EntitlementLimitModal detail={upgradeDetail} onClose={() => setUpgradeDetail(null)} />
    </div>
  )
}

