/**
 * Settings — Global project preferences and application configuration.
 * User/account/password settings live in the Profile page.
 * @module pages/Settings
 */
import { useEffect, useState } from 'react'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import apiClient from '../lib/apiClient'
import { useTutorialStore } from '../stores/tutorialStore'
import { useWalkthroughStore } from '../stores/walkthroughStore'
import { NotionConnectCard } from '../components/integrations/NotionConnectCard'

interface UserPrefs {
  default_partner_style: string
  default_pathway: string
  auto_save: boolean
  discovery_detail_level: string
  email_notifications: boolean
}

const PARTNER_STYLES = [
  { id: 'strategist', label: '🧠 Strategist' },
  { id: 'creative', label: '🎨 Creative' },
  { id: 'analyst', label: '📊 Analyst' },
  { id: 'mentor', label: '🤝 Mentor' },
  { id: 'challenger', label: '⚡ Challenger' },
]

const DETAIL_LEVELS = [
  { id: 'concise', label: 'Concise', desc: 'Short, punchy outputs for fast iteration' },
  { id: 'balanced', label: 'Balanced', desc: 'Good detail without overload (default)' },
  { id: 'detailed', label: 'Detailed', desc: 'In-depth analysis and comprehensive write-ups' },
]

export function Settings() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Tutorial reset
  const [tutorialReset, setTutorialReset] = useState(false)

  // Prefs
  const [prefs, setPrefs] = useState<UserPrefs>({
    default_partner_style: 'strategist',
    default_pathway: 'software_product',
    auto_save: true,
    discovery_detail_level: 'balanced',
    email_notifications: true,
  })

  // Data export
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    apiClient.get('/auth/me').then(({ data }) => {
      if (data.preferences && typeof data.preferences === 'object') {
        setPrefs(p => ({ ...p, ...data.preferences }))
      }
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      await apiClient.patch('/auth/me', { preferences: prefs })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // silent
    } finally {
      setSaving(false)
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const { data } = await apiClient.get('/projects')
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ideai-projects-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // silent
    } finally {
      setExporting(false)
    }
  }

  const updatePref = <K extends keyof UserPrefs>(key: K, value: UserPrefs[K]) => {
    setPrefs(p => ({ ...p, [key]: value }))
  }

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 flex flex-col h-dvh">
        <TopBar title="Settings" subtitle="Global project preferences and configuration" />

        <div className="flex-1 p-4 md:p-6 overflow-y-auto pb-20 md:pb-6">
          <div className="max-w-2xl mx-auto space-y-6">
            {loading ? (
              <div className="text-center py-12 text-text-muted text-sm">Loading settings...</div>
            ) : (
              <>
                {/* ── Default AI Partner ── */}
                <Card>
                  <h3 className="text-sm font-semibold text-white mb-2">Default AI Partner Style</h3>
                  <p className="text-xs text-text-muted mb-4">
                    Pre-selects this partner for every new project. You can always override per-project.
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                    {PARTNER_STYLES.map(p => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => updatePref('default_partner_style', p.id)}
                        className={`text-center rounded-lg px-2 py-2.5 text-xs font-medium transition-all border ${
                          prefs.default_partner_style === p.id
                            ? 'border-accent bg-accent/10 text-accent'
                            : 'border-border bg-white/5 text-text-muted hover:text-white hover:bg-white/10'
                        }`}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </Card>

                {/* ── Discovery Detail Level ── */}
                <Card>
                  <h3 className="text-sm font-semibold text-white mb-2">Discovery Detail Level</h3>
                  <p className="text-xs text-text-muted mb-4">
                    Controls how much depth the AI provides during discovery sessions.
                  </p>
                  <div className="space-y-2">
                    {DETAIL_LEVELS.map(level => (
                      <button
                        key={level.id}
                        type="button"
                        onClick={() => updatePref('discovery_detail_level', level.id)}
                        className={`w-full text-left flex items-start gap-3 rounded-lg px-4 py-3 transition-all border ${
                          prefs.discovery_detail_level === level.id
                            ? 'border-accent bg-accent/10'
                            : 'border-border bg-white/5 hover:bg-white/10'
                        }`}
                      >
                        <div className={`w-3.5 h-3.5 mt-0.5 rounded-full border-2 shrink-0 flex items-center justify-center ${
                          prefs.discovery_detail_level === level.id
                            ? 'border-accent'
                            : 'border-border'
                        }`}>
                          {prefs.discovery_detail_level === level.id && (
                            <div className="w-1.5 h-1.5 rounded-full bg-accent" />
                          )}
                        </div>
                        <div>
                          <p className={`text-sm font-medium ${prefs.discovery_detail_level === level.id ? 'text-accent' : 'text-white'}`}>
                            {level.label}
                          </p>
                          <p className="text-xs text-text-muted">{level.desc}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </Card>

                {/* ── Project Defaults ── */}
                <Card>
                  <h3 className="text-sm font-semibold text-white mb-2">Project Defaults</h3>
                  <p className="text-xs text-text-muted mb-4">
                    Options applied automatically to new projects.
                  </p>

                  <div className="space-y-4">
                    {/* Auto-save toggle */}
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-white font-medium">Auto-save progress</p>
                        <p className="text-xs text-text-muted">Automatically save discovery progress as you go</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => updatePref('auto_save', !prefs.auto_save)}
                        className={`relative w-10 h-5 rounded-full transition-colors ${
                          prefs.auto_save ? 'bg-accent' : 'bg-border'
                        }`}
                      >
                        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                          prefs.auto_save ? 'translate-x-5' : 'translate-x-0.5'
                        }`} />
                      </button>
                    </div>

                    {/* Email notifications toggle */}
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-white font-medium">Email notifications</p>
                        <p className="text-xs text-text-muted">Receive emails about project updates and sharing activity</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => updatePref('email_notifications', !prefs.email_notifications)}
                        className={`relative w-10 h-5 rounded-full transition-colors ${
                          prefs.email_notifications ? 'bg-accent' : 'bg-border'
                        }`}
                      >
                        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                          prefs.email_notifications ? 'translate-x-5' : 'translate-x-0.5'
                        }`} />
                      </button>
                    </div>
                  </div>
                </Card>

                {/* ── Save button ── */}
                <div>
                  <Button onClick={handleSave} disabled={saving}>
                    {saving ? 'Saving...' : saved ? 'Settings Saved!' : 'Save Settings'}
                  </Button>
                </div>

                {/* ── Data & Export ── */}
                <Card>
                  <h3 className="text-sm font-semibold text-white mb-2">Data & Export</h3>
                  <p className="text-xs text-text-muted mb-4">
                    Download all your project data as a JSON file for backup or migration.
                  </p>
                  <Button variant="secondary" size="sm" onClick={handleExport} disabled={exporting}>
                    {exporting ? 'Exporting...' : 'Export All Projects'}
                  </Button>
                </Card>

                {/* ── Integrations ── */}
                <NotionConnectCard />

                {/* ── Tutorial ── */}
                <Card>
                  <h3 className="text-sm font-semibold text-white mb-2">Tutorial & Onboarding</h3>
                  <p className="text-xs text-text-muted mb-3">
                    Replay the step-by-step walkthrough, or reset every ambient hint, beacon, and
                    interlude so they appear again from scratch.
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => useWalkthroughStore.getState().openTour()}
                    >
                      Replay Walkthrough
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        useTutorialStore.getState().resetTutorial()
                        useWalkthroughStore.getState().resetWalkthrough()
                        setTutorialReset(true)
                        setTimeout(() => setTutorialReset(false), 2000)
                      }}
                    >
                      Reset Tutorial
                    </Button>
                    {tutorialReset && (
                      <span className="text-xs text-green-400">Tutorial reset!</span>
                    )}
                  </div>
                </Card>

                {/* ── About ── */}
                <Card>
                  <h3 className="text-sm font-semibold text-white mb-2">About</h3>
                  <p className="text-xs text-text-muted">
                    Ide/AI v0.2.0 — Transform rough ideas into structured design kits.
                  </p>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
