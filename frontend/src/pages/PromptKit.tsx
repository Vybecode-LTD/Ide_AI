/**
 * PromptKit — Generate and manage platform-specific prompt kits.
 * Each kit is a structured, copyable prompt block formatted for a target builder platform.
 * @module pages/PromptKit
 */
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import apiClient from '../lib/apiClient'
import { getEntitlementDetail, type EntitlementDetail } from '../lib/extractError'
import { EntitlementLimitModal } from '../components/ui/EntitlementLimitModal'

interface PromptKitItem {
  id: string
  project_id: string
  platform: string
  content: string
  version: number
  created_at: string
}

const PLATFORMS = [
  { id: 'bubble', label: 'Bubble', desc: 'Data types + workflow instructions' },
  { id: 'claude-code', label: 'Claude Code', desc: 'DB schemas, API endpoints, phased plan' },
  { id: 'bolt', label: 'Bolt.new', desc: 'Single paste-ready prompt + follow-ups' },
  { id: 'cursor', label: 'Cursor', desc: 'VS Code AI composer instructions' },
  { id: 'webflow', label: 'Webflow', desc: 'CMS collections + page structure' },
  { id: 'flutterflow', label: 'FlutterFlow', desc: 'Firebase schema + screen flow' },
  { id: 'replit', label: 'Replit', desc: 'Agent-style step prompts' },
]

export function PromptKit() {
  const { projectId } = useParams<{ projectId: string }>()
  const [kits, setKits] = useState<PromptKitItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPlatform, setSelectedPlatform] = useState('claude-code')
  const [generating, setGenerating] = useState(false)
  const [rewriting, setRewriting] = useState<string | null>(null)
  const [expandedKit, setExpandedKit] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)
  const [upgradeDetail, setUpgradeDetail] = useState<EntitlementDetail | null>(null)

  const fetchKits = useCallback(async () => {
    if (!projectId) return
    try {
      const { data } = await apiClient.get(`/projects/${projectId}/prompts`)
      setKits(data)
    } catch (err) {
      console.error('Failed to fetch prompt kits:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchKits()
  }, [fetchKits])

  const handleGenerate = async () => {
    if (!projectId) return
    setGenerating(true)
    try {
      await apiClient.post(`/projects/${projectId}/prompts/generate`, {
        platform: selectedPlatform,
      })
      await fetchKits()
    } catch (err) {
      const ent = getEntitlementDetail(err)
      if (ent) setUpgradeDetail(ent)
      else console.error('Generate failed:', err)
    } finally {
      setGenerating(false)
    }
  }

  const handleRewrite = async (kitId: string) => {
    if (!projectId) return
    setRewriting(kitId)
    try {
      await apiClient.post(`/projects/${projectId}/prompts/${kitId}/rewrite`)
      await fetchKits()
    } catch (err) {
      console.error('Rewrite failed:', err)
    } finally {
      setRewriting(null)
    }
  }

  const handleCopy = async (kitId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(kitId)
      setTimeout(() => setCopied(null), 2000)
    } catch {
      // fallback
    }
  }

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })

  // Group kits by platform, newest first
  const grouped = PLATFORMS.map((p) => ({
    ...p,
    kits: kits
      .filter((k) => k.platform === p.id)
      .sort((a, b) => b.version - a.version),
  })).filter((g) => g.kits.length > 0)

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar projectId={projectId} />
      <div className="ml-0 md:ml-[232px] pb-14 md:pb-0 flex-1 flex flex-col h-screen">
        <TopBar title="Prompt Kit" subtitle="Platform-specific prompt blocks for your builder tool" />

        <div className="flex-1 p-4 md:p-6 overflow-y-auto pb-20 md:pb-6">
          <div className="max-w-4xl mx-auto">
            {/* Generate section */}
            <Card className="mb-8">
              <h2 className="text-sm font-semibold text-white mb-3">
                Generate New Prompt Kit
              </h2>
              <p className="text-xs text-text-muted mb-4">
                Select a target platform and generate structured prompts from your design sheet and feature blocks.
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 mb-4">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPlatform(p.id)}
                    className={`text-left rounded-lg border px-3 py-2 transition-all text-xs ${
                      selectedPlatform === p.id
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border bg-white/5 text-text-muted hover:border-white/20 hover:text-white'
                    }`}
                  >
                    <span className="font-medium block">{p.label}</span>
                    <span className="text-[10px] opacity-60">{p.desc}</span>
                  </button>
                ))}
              </div>
              <Button onClick={handleGenerate} disabled={generating}>
                {generating ? 'Generating...' : `Generate for ${PLATFORMS.find((p) => p.id === selectedPlatform)?.label}`}
              </Button>
              {generating && (
                <p className="text-xs text-text-muted mt-2">
                  This may take 15-30 seconds while AI crafts your prompts.
                </p>
              )}
            </Card>

            {/* Existing kits */}
            {loading ? (
              <p className="text-center text-text-muted text-sm py-8">Loading prompt kits...</p>
            ) : grouped.length === 0 ? (
              <Card className="text-center py-12">
                <p className="text-4xl mb-3 opacity-30">&#x2318;</p>
                <p className="text-text-muted text-sm">
                  No prompt kits generated yet. Select a platform above and generate one.
                </p>
              </Card>
            ) : (
              <div className="space-y-6">
                {grouped.map((group) => (
                  <div key={group.id}>
                    <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                      {group.label}
                      <span className="text-[10px] text-text-muted font-normal">
                        {group.kits.length} version{group.kits.length !== 1 ? 's' : ''}
                      </span>
                    </h3>
                    <div className="space-y-2">
                      {group.kits.map((kit) => {
                        const isExpanded = expandedKit === kit.id
                        return (
                          <Card key={kit.id}>
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono text-accent bg-accent/10 px-1.5 py-0.5 rounded">
                                  v{kit.version}
                                </span>
                                <span className="text-[10px] text-text-muted">
                                  {formatDate(kit.created_at)}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleCopy(kit.id, kit.content)}
                                >
                                  {copied === kit.id ? 'Copied!' : 'Copy'}
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleRewrite(kit.id)}
                                  disabled={rewriting === kit.id}
                                >
                                  {rewriting === kit.id ? '...' : 'Rewrite'}
                                </Button>
                                <button
                                  onClick={() => setExpandedKit(isExpanded ? null : kit.id)}
                                  className="text-xs text-text-muted hover:text-white transition-colors px-2"
                                >
                                  {isExpanded ? 'Collapse' : 'Expand'}
                                </button>
                              </div>
                            </div>
                            {isExpanded && (
                              <pre className="mt-3 p-4 bg-black/30 rounded-lg text-xs text-white/80 font-mono whitespace-pre-wrap overflow-x-auto max-h-[60vh] overflow-y-auto border border-white/5">
                                {kit.content}
                              </pre>
                            )}
                            {!isExpanded && (
                              <p className="text-xs text-text-muted truncate mt-1">
                                {kit.content.slice(0, 120)}...
                              </p>
                            )}
                          </Card>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <EntitlementLimitModal detail={upgradeDetail} onClose={() => setUpgradeDetail(null)} />
    </div>
  )
}
