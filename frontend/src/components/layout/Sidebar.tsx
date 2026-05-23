/**
 * Sidebar — Responsive navigation.
 * Desktop: Fixed left sidebar (232px) with logo + labels.
 * Mobile: Fixed bottom nav bar with icons only + hamburger for overflow.
 * Shows "Back to Project" when user navigates to Home with an active project.
 * Project module items are driven by the active pathway from pathwayStore.
 * @module components/layout/Sidebar
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { usePathwayStore } from '../../stores/pathwayStore'
import { useModulePathwayStore } from '../../stores/modulePathwayStore'
import { useInboxStore } from '../../stores/inboxStore'
import { UserButton, useAuth } from '@clerk/clerk-react'
import { useAuthStore } from '../../stores/authStore'

const NAV_ITEMS = [
  { path: '/home', label: 'Home', icon: '\u2726' },
  { path: '/inbox', label: 'Inbox', icon: '\u{1F4EC}' },
  { path: '/library', label: 'Library', icon: '\u{1F4DA}' },
  { path: '/settings', label: 'Settings', icon: '\u2699' },
]

/** Discovery-only item shown before pathway is locked */
const DISCOVERY_ONLY = [
  { path: '/discovery', label: 'Discovery', icon: '\u{1F50D}' },
]

/** Maps module IDs from the 47-module library to existing page routes */
const EXISTING_MODULE_ROUTES: Record<string, string> = {
  design_blocks_board: '/blocks',
  pipeline_builder: '/pipeline',
  market_analysis: '/market',
  sprint_planner: '/sprints',
  pitch_mode: '/pitch',
  export_system: '/exports',
}

/** Icons for dynamic modules by group */
const GROUP_ICONS: Record<string, string> = {
  Definition: '\u{1F3AF}',
  'Research & Validation': '\u{1F50D}',
  Planning: '\u{1F4CB}',
  Design: '\u{1F3A8}',
  Execution: '\u26A1',
  Delivery: '\u{1F4E6}',
  Existing: '\u2699',
}

const ACTIVE_PROJECT_KEY = 'ideai_active_project'
const ACTIVE_PROJECT_PATH_KEY = 'ideai_active_path'
const ACTIVE_PROJECT_TS_KEY = 'ideai_active_ts'
const INACTIVITY_TIMEOUT_MS = 15 * 60 * 1000 // 15 minutes
const INBOX_POLL_MS = 60_000 // Refresh inbox count every 60s

export function Sidebar({ projectId }: { projectId?: string }) {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const { user, fetchUser } = useAuthStore()
  const { fetchPathways } = usePathwayStore()
  const { assembledModules, pathway } = useModulePathwayStore()
  const { isSignedIn } = useAuth()
  const inboxCount = useInboxStore((s) => s.count)
  const refreshInboxCount = useInboxStore((s) => s.refresh)

  // Fetch user + pathways on mount (deduped inside stores)
  useEffect(() => { fetchUser() }, [fetchUser])
  useEffect(() => { fetchPathways() }, [fetchPathways])

  // ── Inbox unread badge ─────────────────────────────────────────
  // Polls every 60s (only when signed in), and refreshes on transitions
  // AWAY from /inbox (where the user likely modified items).
  // Inbox page itself calls store.refresh() / store.adjust() after mutations
  // for instant feedback.
  useEffect(() => {
    if (!isSignedIn) return
    refreshInboxCount()
    const id = setInterval(refreshInboxCount, INBOX_POLL_MS)
    return () => clearInterval(id)
  }, [isSignedIn, refreshInboxCount])

  // Track previous path so we only refresh on actual /inbox → other transitions,
  // not on every render or every route change.
  const prevPathRef = useRef(location.pathname)
  useEffect(() => {
    const prev = prevPathRef.current
    prevPathRef.current = location.pathname
    if (prev === '/inbox' && location.pathname !== '/inbox' && isSignedIn) {
      refreshInboxCount()
    }
  }, [location.pathname, isSignedIn, refreshInboxCount])

  // Build project items from assembled dynamic modules
  // During discovery (before PathwayReview locks the pathway), only show Discovery
  const projectItems = useMemo(() => {
    const pathwayReady = pathway?.status === 'active' || pathway?.status === 'complete'
    if (!pathwayReady || assembledModules.length === 0) {
      // Pre-pathway: only Discovery visible
      return DISCOVERY_ONLY
    }

    // Discovery is always first
    const items: Array<{ path: string; label: string; icon: string }> = [
      { path: '/discovery', label: 'Discovery', icon: '\u{1F50D}' },
    ]

    for (const m of assembledModules) {
      const existingRoute = EXISTING_MODULE_ROUTES[m.module_id]
      if (existingRoute) {
        items.push({ path: existingRoute, label: m.label, icon: GROUP_ICONS[m.group] || '\u2699' })
      } else {
        // AI-guided module → links to module-session
        items.push({
          path: `/module-session-nav/${m.module_id}`,
          label: m.label,
          icon: GROUP_ICONS[m.group] || '\u{1F4AC}',
        })
      }
    }

    return items
  }, [assembledModules, pathway?.status])

  // Persist active project + timestamp when user is inside a project.
  // Uses refs to write to localStorage (external system) and sync derived
  // state without triggering cascading renders.
  useEffect(() => {
    if (projectId) {
      localStorage.setItem(ACTIVE_PROJECT_KEY, projectId)
      localStorage.setItem(ACTIVE_PROJECT_PATH_KEY, location.pathname)
      localStorage.setItem(ACTIVE_PROJECT_TS_KEY, Date.now().toString())
    }
  }, [projectId, location.pathname])

  // Derive saved project from localStorage — read once on mount.
  const [savedProjectId, setSavedProjectId] = useState<string | null>(() => {
    const id = localStorage.getItem(ACTIVE_PROJECT_KEY)
    const ts = localStorage.getItem(ACTIVE_PROJECT_TS_KEY)
    if (id && ts && Date.now() - Number(ts) < INACTIVITY_TIMEOUT_MS) return id
    localStorage.removeItem(ACTIVE_PROJECT_KEY)
    localStorage.removeItem(ACTIVE_PROJECT_PATH_KEY)
    localStorage.removeItem(ACTIVE_PROJECT_TS_KEY)
    return null
  })
  const [savedPath, setSavedPath] = useState<string | null>(() =>
    savedProjectId ? localStorage.getItem(ACTIVE_PROJECT_PATH_KEY) : null,
  )

  // Keep derived state in sync when projectId changes (external nav).
  // Uses state-based previous-value pattern (no refs during render).
  const [prevProjectId, setPrevProjectId] = useState(projectId)
  const [prevPathname, setPrevPathname] = useState(location.pathname)
  if (projectId && (projectId !== prevProjectId || location.pathname !== prevPathname)) {
    setPrevProjectId(projectId)
    setPrevPathname(location.pathname)
    setSavedProjectId(projectId)
    setSavedPath(location.pathname)
  }

  // Show "Back to Project" only on Home or Settings when user just left a project
  const isOnHomePage = location.pathname === '/home' || location.pathname === '/settings'
  const showBackToProject = isOnHomePage && savedProjectId && !projectId

  const allItems = projectId
    ? [...NAV_ITEMS, ...projectItems]
    : NAV_ITEMS

  const mobileBarItems = allItems.slice(0, 4)
  const mobileOverflowItems = allItems.slice(4)

  const isActive = (item: { path: string }) =>
    item.path === '/home'
      ? location.pathname === '/home'
      : location.pathname.startsWith(`${item.path}/`) || location.pathname === item.path

  const buildTo = (item: { path: string }) => {
    if (!projectId || !projectItems.some((p) => p.path === item.path)) return item.path
    // Dynamic AI modules use /module-session/{projectId}/{moduleId}
    if (item.path.startsWith('/module-session-nav/')) {
      const moduleId = item.path.replace('/module-session-nav/', '')
      return `/module-session/${projectId}/${moduleId}`
    }
    return `${item.path}/${projectId}`
  }

  return (
    <>
      {/* ── Desktop sidebar ── */}
      <aside className="hidden md:flex fixed left-0 top-0 h-screen w-[232px] bg-surface border-r border-border z-50 flex-col overflow-hidden">
        <Link to="/home" className="px-4 py-3 flex items-center border-b border-border">
          <img src="/logo.png" alt="Ide/AI — Home" className="w-[200px] object-contain" />
        </Link>

        <nav className="flex-1 py-4 flex flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const showInboxBadge = item.path === '/inbox' && inboxCount > 0
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  isActive(item)
                    ? 'text-accent bg-accent-dim'
                    : 'text-text-muted hover:text-white hover:bg-white/5'
                }`}
              >
                <span className="shrink-0 text-base">{item.icon}</span>
                <span className="whitespace-nowrap flex-1">{item.label}</span>
                {showInboxBadge && (
                  <span
                    aria-label={`${inboxCount} unread inbox item${inboxCount === 1 ? '' : 's'}`}
                    className="shrink-0 min-w-[20px] h-5 px-1.5 rounded-full bg-accent text-background text-[10px] font-bold flex items-center justify-center"
                  >
                    {inboxCount > 99 ? '99+' : inboxCount}
                  </span>
                )}
              </Link>
            )
          })}

          {/* Back to Project button — shown when user leaves a project */}
          {showBackToProject && (
            <>
              <div className="mx-4 my-2 border-t border-border" />
              <Link
                to={savedPath || `/discovery/${savedProjectId}`}
                className="flex items-center gap-3 px-4 py-2.5 text-sm text-accent bg-accent/5 border border-accent/20 mx-2 rounded-lg hover:bg-accent/10 transition-colors"
              >
                <span className="whitespace-nowrap">Back to Project</span>
              </Link>
            </>
          )}

          {projectId && (
            <>
              <div className="mx-4 my-2 border-t border-border" />
              <div className="flex-1 overflow-y-auto">
              {projectItems.map((item) => {
                const href = item.path.startsWith('/module-session-nav/')
                  ? `/module-session/${projectId}/${item.path.replace('/module-session-nav/', '')}`
                  : `${item.path}/${projectId}`
                return (
                <Link
                  key={item.path}
                  to={href}
                  className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                    isActive(item)
                      ? 'text-accent bg-accent-dim'
                      : 'text-text-muted hover:text-white hover:bg-white/5'
                  }`}
                >
                  <span className="shrink-0 text-base">{item.icon}</span>
                  <span className="whitespace-nowrap truncate">{item.label}</span>
                </Link>
                )
              })}
              </div>
            </>
          )}
        </nav>

        {/* Profile container */}
        <div className="mx-2 mb-3 px-3 py-2.5 rounded-lg border border-border flex items-center gap-3">
          <UserButton afterSignOutUrl="/" />
          {user && (
            <Link to="/profile" className="min-w-0 flex-1 hover:opacity-80 transition-opacity">
              <p className="text-xs text-white font-medium truncate">
                {user.display_name || user.name || user.email}
              </p>
              <p className="text-[10px] text-text-muted truncate capitalize">
                {user.account_type || 'free'} plan
              </p>
            </Link>
          )}
        </div>
      </aside>

      {/* ── Mobile bottom nav ── */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 bg-surface border-t border-border z-50 flex items-center justify-around px-2"
        style={{
          /* h-14 + safe-area inset so iPhone home indicator doesn't overlap nav */
          height: 'calc(3.5rem + env(safe-area-inset-bottom, 0px))',
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
        aria-label="Mobile navigation"
      >
        {showBackToProject && (
          <Link
            to={savedPath || `/discovery/${savedProjectId}`}
            className="flex flex-col items-center justify-center gap-0.5 min-h-[44px] min-w-[44px] px-2 rounded-lg text-xs text-accent"
            aria-label="Back to Project"
          >
            <span className="text-[10px] leading-tight">Back to Project</span>
          </Link>
        )}

        {mobileBarItems.map((item) => {
          const showInboxBadge = item.path === '/inbox' && inboxCount > 0
          return (
            <Link
              key={item.path}
              to={buildTo(item)}
              className={`relative flex flex-col items-center justify-center gap-0.5 min-h-[44px] min-w-[44px] px-2 rounded-lg text-xs transition-colors ${
                isActive(item)
                  ? 'text-accent'
                  : 'text-text-muted'
              }`}
              aria-label={
                showInboxBadge
                  ? `${item.label}, ${inboxCount} unread item${inboxCount === 1 ? '' : 's'}`
                  : item.label
              }
              aria-current={isActive(item) ? 'page' : undefined}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="text-[10px] leading-tight">{item.label}</span>
              {showInboxBadge && (
                <span
                  aria-hidden="true"
                  className="absolute top-0 right-0 min-w-[16px] h-4 px-1 rounded-full bg-accent text-background text-[9px] font-bold flex items-center justify-center"
                >
                  {inboxCount > 99 ? '99+' : inboxCount}
                </span>
              )}
            </Link>
          )
        })}

        {mobileOverflowItems.length > 0 && (
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className={`flex flex-col items-center justify-center gap-0.5 min-h-[44px] min-w-[44px] px-2 rounded-lg text-xs transition-colors ${
              mobileMenuOpen ? 'text-accent' : 'text-text-muted'
            }`}
            aria-label="More navigation options"
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-overflow-menu"
          >
            <span className="text-lg">{'\u2022\u2022\u2022'}</span>
            <span className="text-[10px] leading-tight">More</span>
          </button>
        )}
      </nav>

      {/* ── Mobile overflow menu ── */}
      {mobileMenuOpen && mobileOverflowItems.length > 0 && (
        <>
          <div
            className="md:hidden fixed inset-0 bg-black/50 z-40"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div
            id="mobile-overflow-menu"
            role="menu"
            className="md:hidden fixed left-0 right-0 bg-surface border-t border-border z-50 py-2"
            style={{ bottom: 'calc(3.5rem + env(safe-area-inset-bottom, 0px))' }}
            onKeyDown={(e) => { if (e.key === 'Escape') setMobileMenuOpen(false) }}
          >
            <div className="px-4 py-2 flex items-center border-b border-border mb-2">
              <img src="/logo.png" alt="Ide/AI" className="w-[120px] object-contain" />
            </div>
            {mobileOverflowItems.map((item) => {
              const showInboxBadge = item.path === '/inbox' && inboxCount > 0
              return (
                <Link
                  key={item.path}
                  to={buildTo(item)}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 text-sm transition-colors ${
                    isActive(item)
                      ? 'text-accent bg-accent-dim'
                      : 'text-text-muted hover:text-white hover:bg-white/5'
                  }`}
                >
                  <span className="text-base">{item.icon}</span>
                  <span className="flex-1">{item.label}</span>
                  {showInboxBadge && (
                    <span
                      aria-label={`${inboxCount} unread inbox item${inboxCount === 1 ? '' : 's'}`}
                      className="shrink-0 min-w-[20px] h-5 px-1.5 rounded-full bg-accent text-background text-[10px] font-bold flex items-center justify-center"
                    >
                      {inboxCount > 99 ? '99+' : inboxCount}
                    </span>
                  )}
                </Link>
              )
            })}
          </div>
        </>
      )}
    </>
  )
}
