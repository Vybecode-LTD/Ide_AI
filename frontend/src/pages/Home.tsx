/**
 * Home -- Idea input landing page. Users first pick a category (CategorySelect),
 * then describe their idea, choose an AI partner, and start discovery.
 * @module pages/Home
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '../components/ui/Button'
import { Sidebar } from '../components/layout/Sidebar'
import { IdeaNebulaCanvas } from '../components/nebula/IdeaNebulaCanvas'
import { TemplateGrid, type Template } from '../components/home/TemplateGrid'
import { CategorySelect } from './CategorySelect'
import type { PartnerStyleMeta } from '../types/project'
import apiClient from '../lib/apiClient'
import { getEntitlementDetail, type EntitlementDetail } from '../lib/extractError'
import { UpgradeModal } from '../components/ui/UpgradeModal'
import { useAuthStore } from '../stores/authStore'
import { PulseBeacon, Whisper } from '../components/tutorial'

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
  useEffect(() => {
    if (!billingSuccess) return
    fetchUser() // Refresh user to get updated account_type
    setSearchParams({}, { replace: true }) // Clean URL
    const timer = setTimeout(() => setBillingSuccess(false), 5000)
    return () => clearTimeout(timer)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const [loading, setLoading] = useState(false)
  const [upgradeDetail, setUpgradeDetail] = useState<EntitlementDetail | null>(null)

  // Template state
  const [activeTemplate, setActiveTemplate] = useState<Template | null>(null)

  // AI Partner state
  const [partnerStyle, setPartnerStyle] = useState('strategist')
  const [allPartners, setAllPartners] = useState<PartnerStyleMeta[]>(() => _partnerCache ?? [])

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

  /** Create the project and navigate to discovery. */
  const createProject = async () => {
    // If a template is active, use the template endpoint
    if (activeTemplate) {
      const { data } = await apiClient.post(`/templates/${activeTemplate.id}/use`, {
        extra_description: idea.trim() || undefined,
        ai_partner_style: partnerStyle,
      })
      navigate(`/discovery/${data.project_id}`)
      return
    }

    const { data } = await apiClient.post('/projects', {
      name: idea.slice(0, 100),
      description: idea,
      pathway_id: 'software_product',
      ai_partner_style: partnerStyle,
      primary_category: selectedCategory,
    })
    navigate(`/discovery/${data.id}`)
  }

  /** Main submit handler — create project directly (category already chosen). */
  const handleSubmit = async () => {
    if (!idea.trim() && !activeTemplate) return
    setLoading(true)
    try {
      await createProject()
    } catch (err) {
      const ent = getEntitlementDetail(err)
      if (ent) setUpgradeDetail(ent)
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

      <main className="ml-0 md:ml-[232px] flex flex-col items-center justify-center min-h-screen px-4 md:px-6 pb-14 md:pb-0">
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

          <div className="mb-2" />

          {/* Submit */}
          <PulseBeacon id="home:start">
            <Button size="lg" onClick={handleSubmit} disabled={(!idea.trim() && !activeTemplate) || loading}>
              {loading ? 'Creating...' : 'Start Discovery \u2192'}
            </Button>
          </PulseBeacon>
        </motion.div>

        {/* Template grid — filtered to selected category */}
        <TemplateGrid
          onSelect={(t) => setActiveTemplate(prev => prev?.id === t.id ? null : t)}
          selectedId={activeTemplate?.id}
          category={selectedCategory}
        />

      </main>

      <UpgradeModal detail={upgradeDetail} onClose={() => setUpgradeDetail(null)} />
    </div>
  )
}

