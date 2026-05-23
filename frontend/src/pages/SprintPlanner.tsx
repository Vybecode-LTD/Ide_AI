/**
 * SprintPlanner — AI-powered sprint planning with milestones, board, and Gantt views.
 * @module pages/SprintPlanner
 */
import { Fragment, useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import apiClient, { getAuthToken } from '../lib/apiClient'
import toast from 'react-hot-toast'
import { downloadBlob } from '../lib/exportUtils'
import { extractError, type EntitlementDetail } from '../lib/extractError'
import { EntitlementLimitModal } from '../components/ui/EntitlementLimitModal'

interface Task {
  id: string
  block_id: string
  block_name: string
  description: string
  effort: string
  priority: string
  status: string
}

interface Sprint {
  id: string
  name: string
  milestone_id: string
  duration_weeks: number
  start_week: number
  tasks: Task[]
}

interface Milestone {
  id: string
  name: string
  description: string
  target_date: string
  blocks: string[]
  status: string
}

interface TimelineItem {
  id: string
  name: string
  sprint: string
  start_week: number
  end_week: number
  effort: string
  dependencies: string[]
}

interface SprintPlanData {
  id: string
  project_id: string
  milestones: Milestone[] | null
  sprints: Sprint[] | null
  timeline: TimelineItem[] | null
  status: string
  created_at: string | null
  updated_at: string | null
}

type ViewTab = 'milestones' | 'board' | 'timeline'

export function SprintPlanner() {
  const { projectId } = useParams<{ projectId: string }>()
  const [plan, setPlan] = useState<SprintPlanData | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusMessage, setStatusMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [activeView, setActiveView] = useState<ViewTab>('milestones')
  const [upgradeDetail, setUpgradeDetail] = useState<EntitlementDetail | null>(null)

  // Fetch existing plan from DB
  const fetchPlan = useCallback(async () => {
    if (!projectId) return
    try {
      const { data } = await apiClient.get(`/sprints/${projectId}`)
      setPlan(data)
    } catch {
      // No plan yet — that's fine
    }
  }, [projectId])

  // Initial load
  useEffect(() => {
    fetchPlan().finally(() => setLoading(false))
  }, [fetchPlan])

  // Generate via SSE
  const generate = useCallback(async () => {
    if (!projectId || generating) return
    setGenerating(true)
    setProgress(0)
    setErrorMessage('')
    setStatusMessage('Analyzing project blocks...')

    const token = await getAuthToken()
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    const hasPlanAlready = plan && plan.status === 'complete'
    let receivedPlan = false

    try {
      const url = `${baseUrl}/sprints/${projectId}/generate${hasPlanAlready ? '?force=true' : ''}`
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        if (response.status === 403) {
          try {
            const body = await response.json()
            const d = body?.detail
            if (d && (d.code === 'project_limit_reached' || d.code === 'feature_limit_reached')) {
              setUpgradeDetail(d as EntitlementDetail)
              return
            }
          } catch { /* not JSON */ }
        }
        throw new Error(`HTTP ${response.status}`)
      }
      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          buffer += decoder.decode()
        } else {
          buffer += decoder.decode(value, { stream: true })
        }

        const lines = buffer.split('\n')
        buffer = done ? '' : (lines.pop() || '')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'plan_start') {
              setStatusMessage('Generating sprint plan...')
            } else if (data.type === 'plan_progress') {
              setProgress(data.progress || 0)
              setStatusMessage(data.message || data.label || 'Generating...')
            } else if (data.type === 'section_complete') {
              setProgress(data.progress || 0)
              setStatusMessage(`${data.section || 'Section'} complete`)
            } else if (data.type === 'plan_complete') {
              setProgress(1)
              setStatusMessage('Complete!')
              receivedPlan = true
              if (data.plan) {
                setPlan(data.plan)
              }
            } else if (data.type === 'error') {
              setErrorMessage(data.message || 'Generation failed')
            }
          } catch { /* skip malformed SSE line */ }
        }

        if (done) break
      }

      // Fallback: if we didn't get plan data from SSE, fetch from DB
      if (!receivedPlan || !plan) {
        await fetchPlan()
      }
    } catch (err) {
      console.error('Sprint generation error:', err)
      setErrorMessage('Generation failed. Please try again.')
      toast.error(extractError(err, "Couldn't generate sprint plan."))
    } finally {
      setGenerating(false)
    }
  }, [projectId, generating, plan, fetchPlan])

  const exportCSV = async () => {
    if (!projectId) return
    try {
      const response = await apiClient.get(`/sprints/${projectId}/export`, { responseType: 'blob' })
      downloadBlob(response.data, `sprint-plan-${projectId}.csv`)
    } catch (err) {
      console.error('Export failed:', err)
      toast.error(extractError(err, "Couldn't export sprint plan."))
    }
  }

  // AI sometimes wraps arrays: {"milestones": [...]} instead of [...].
  // Extract the inner array when that happens.
  const extractArr = (val: unknown, key: string): unknown[] => {
    if (Array.isArray(val)) return val
    if (val && typeof val === 'object' && key in (val as Record<string, unknown>)) {
      const inner = (val as Record<string, unknown>)[key]
      if (Array.isArray(inner)) return inner
    }
    return []
  }

  const milestones = extractArr(plan?.milestones, 'milestones') as Milestone[]
  const sprints = extractArr(plan?.sprints, 'sprints') as Sprint[]
  const timeline = extractArr(plan?.timeline, 'timeline') as TimelineItem[]
  const hasPlan = plan && plan.status === 'complete'

  // Debug: log plan data shape to help diagnose rendering issues
  useEffect(() => {
    if (plan) {
      console.log('[SprintPlanner] plan.status:', plan.status)
      console.log('[SprintPlanner] milestones type:', typeof plan.milestones, Array.isArray(plan.milestones) ? `array(${(plan.milestones as unknown[]).length})` : plan.milestones)
      console.log('[SprintPlanner] sprints type:', typeof plan.sprints, Array.isArray(plan.sprints) ? `array(${(plan.sprints as unknown[]).length})` : plan.sprints)
      console.log('[SprintPlanner] timeline type:', typeof plan.timeline, Array.isArray(plan.timeline) ? `array(${(plan.timeline as unknown[]).length})` : plan.timeline)
      console.log('[SprintPlanner] extracted:', { milestones: milestones.length, sprints: sprints.length, timeline: timeline.length })
    }
  }, [plan, milestones.length, sprints.length, timeline.length])

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar projectId={projectId} />
      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 min-w-0 flex flex-col h-dvh">
        <TopBar title="Sprint Planner" subtitle="AI-generated roadmap & sprint breakdown">
          {hasPlan && (
            <>
              <Button variant="ghost" onClick={exportCSV}>Export CSV</Button>
              <Button variant="secondary" onClick={generate} disabled={generating}>Regenerate</Button>
            </>
          )}
          {!hasPlan && !generating && (
            <Button onClick={generate} disabled={generating}>Generate Plan</Button>
          )}
        </TopBar>

        <div className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden p-4 md:p-6 pb-20 md:pb-6">
          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {/* Generating */}
          {generating && (
            <div className="max-w-lg mx-auto py-16 text-center">
              <div className="w-12 h-12 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-6" />
              <h3 className="text-lg font-semibold text-white mb-2">Generating Sprint Plan</h3>
              <p className="text-sm text-text-muted mb-4">{statusMessage}</p>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden max-w-xs mx-auto">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-500"
                  style={{ width: `${Math.round(progress * 100)}%` }}
                />
              </div>
            </div>
          )}

          {/* Error banner */}
          {errorMessage && !generating && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-red-400/10 border border-red-400/20 text-red-400 text-sm">
              {errorMessage}
            </div>
          )}

          {/* Empty state */}
          {!loading && !generating && !hasPlan && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="text-5xl mb-4 opacity-40">🏃</div>
              <h3 className="text-xl font-semibold text-white mb-2">No Sprint Plan Yet</h3>
              <p className="text-sm text-text-muted mb-6 max-w-md">
                Generate an AI-powered sprint plan from your project blocks. The AI will analyze
                your features, priorities, and tech stack to create milestones and sprints.
              </p>
              <Button size="lg" onClick={generate}>Generate Sprint Plan</Button>
            </div>
          )}

          {/* Plan views */}
          {!loading && !generating && hasPlan && (
            <>
              {/* View tabs */}
              <div className="flex gap-1 mb-6 bg-surface/30 border border-border rounded-lg p-1 w-fit">
                {([
                  { key: 'milestones' as ViewTab, label: 'Milestones', icon: '🎯' },
                  { key: 'board' as ViewTab, label: 'Sprint Board', icon: '📋' },
                  { key: 'timeline' as ViewTab, label: 'Timeline', icon: '📊' },
                ] as const).map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveView(tab.key)}
                    className={`flex items-center gap-2 px-4 py-2 text-xs rounded-md transition-colors ${
                      activeView === tab.key
                        ? 'bg-accent/15 text-accent font-medium'
                        : 'text-text-muted hover:text-white hover:bg-white/5'
                    }`}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.label}</span>
                  </button>
                ))}
              </div>

              {/* Milestones View */}
              {activeView === 'milestones' && milestones.length === 0 && (
                <div className="text-center py-16">
                  <p className="text-sm text-text-muted">No milestones data. Try regenerating the plan.</p>
                  <Button variant="secondary" className="mt-4" onClick={generate} disabled={generating}>Regenerate</Button>
                </div>
              )}
              {activeView === 'milestones' && milestones.length > 0 && (
                <div className="space-y-4">
                  {milestones.map((m, i) => {
                    const mSprints = sprints.filter(s => s.milestone_id === m.id)
                    const totalTasks = mSprints.reduce((acc, s) => acc + (s.tasks?.length || 0), 0)
                    const doneTasks = mSprints.reduce((acc, s) => acc + (s.tasks?.filter(t => t.status === 'done').length || 0), 0)
                    const pct = totalTasks > 0 ? Math.round((doneTasks / totalTasks) * 100) : 0

                    return (
                      <Card key={m.id} glow={i === 0}>
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs bg-accent/15 text-accent px-2 py-0.5 rounded-full font-medium">
                                Milestone {i + 1}
                              </span>
                              <span className="text-xs text-text-muted">{m.target_date}</span>
                            </div>
                            <h3 className="text-base font-semibold text-white">{m.name}</h3>
                            <p className="text-xs text-text-muted mt-1">{m.description}</p>
                          </div>
                          <div className="text-right">
                            <div className="text-lg font-bold text-accent">{pct}%</div>
                            <div className="text-[10px] text-text-muted">{doneTasks}/{totalTasks} tasks</div>
                          </div>
                        </div>
                        {/* Progress bar */}
                        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <div className="h-full bg-accent rounded-full transition-all" style={{ width: `${pct}%` }} />
                        </div>
                        {/* Sprint cards under milestone */}
                        {mSprints.length > 0 && (
                          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                            {mSprints.map(s => (
                              <div key={s.id} className="bg-white/3 border border-border/50 rounded-lg p-3">
                                <div className="text-xs font-medium text-white mb-2">{s.name} ({s.duration_weeks}w)</div>
                                <div className="space-y-1">
                                  {s.tasks?.map(t => (
                                    <div key={t.id} className="flex items-center gap-2 text-xs">
                                      <span className={`w-1.5 h-1.5 rounded-full ${
                                        t.status === 'done' ? 'bg-emerald-400' :
                                        t.status === 'in_progress' ? 'bg-accent' : 'bg-white/20'
                                      }`} />
                                      <span className="text-text-muted flex-1 truncate">{t.block_name}</span>
                                      <span className={`px-1 py-0.5 rounded text-[9px] font-medium ${
                                        t.priority === 'mvp' ? 'bg-accent/15 text-accent' : 'bg-amber-500/15 text-amber-400'
                                      }`}>{t.effort}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </Card>
                    )
                  })}
                </div>
              )}

              {/* Sprint Board View */}
              {activeView === 'board' && sprints.length === 0 && (
                <div className="text-center py-16">
                  <p className="text-sm text-text-muted">No sprint data. Try regenerating the plan.</p>
                  <Button variant="secondary" className="mt-4" onClick={generate} disabled={generating}>Regenerate</Button>
                </div>
              )}
              {activeView === 'board' && sprints.length > 0 && (
                <div className="flex gap-4 overflow-x-auto pb-4 min-w-0 w-full">
                  {sprints.map(s => (
                    <div key={s.id} className="min-w-[280px] max-w-[320px] flex-shrink-0">
                      <div className="bg-surface/50 border border-border rounded-xl p-4">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="text-sm font-semibold text-white">{s.name}</h3>
                          <span className="text-[10px] text-text-muted">W{s.start_week}-{s.start_week + s.duration_weeks - 1}</span>
                        </div>
                        <div className="space-y-2">
                          {s.tasks?.map(t => (
                            <div key={t.id} className="bg-white/5 border border-border/50 rounded-lg p-3">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-medium text-white">{t.block_name}</span>
                                <span className={`w-2 h-2 rounded-full ${
                                  t.status === 'done' ? 'bg-emerald-400' :
                                  t.status === 'in_progress' ? 'bg-accent' : 'bg-white/20'
                                }`} />
                              </div>
                              <p className="text-[10px] text-text-muted line-clamp-2">{t.description}</p>
                              <div className="flex gap-1 mt-2">
                                <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                                  t.priority === 'mvp' ? 'bg-accent/15 text-accent' : 'bg-amber-500/15 text-amber-400'
                                }`}>{t.priority.toUpperCase()}</span>
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/10 text-text-muted font-medium">{t.effort}</span>
                              </div>
                            </div>
                          ))}
                          {(!s.tasks || s.tasks.length === 0) && (
                            <p className="text-xs text-text-muted text-center py-4">No tasks</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Timeline / Gantt View */}
              {activeView === 'timeline' && (
                <GanttChart timeline={timeline} />
              )}
            </>
          )}
        </div>
      </div>

      <EntitlementLimitModal detail={upgradeDetail} onClose={() => setUpgradeDetail(null)} />
    </div>
  )
}

/** Simple CSS Grid-based Gantt chart */
function GanttChart({ timeline }: { timeline: TimelineItem[] }) {
  if (!timeline.length) {
    return <p className="text-sm text-text-muted text-center py-8">No timeline data available.</p>
  }

  const maxWeek = Math.max(...timeline.map(t => t.end_week), 12)
  const totalWeeks = Math.max(maxWeek, 8)

  return (
    <div className="overflow-x-auto border border-border rounded-xl">
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `200px repeat(${totalWeeks}, minmax(50px, 1fr))`,
        }}
      >
        {/* Header row */}
        <div className="sticky left-0 z-10 bg-surface border-b border-r border-border p-2 text-xs text-text-muted font-medium">
          Task
        </div>
        {Array.from({ length: totalWeeks }, (_, i) => (
          <div key={i} className="p-2 text-[10px] text-text-muted text-center border-b border-r border-border/50 bg-surface/50">
            W{i + 1}
          </div>
        ))}

        {/* Task rows */}
        {timeline.map((item, rowIdx) => (
          <Fragment key={item.id}>
            <div className={`sticky left-0 z-10 bg-surface border-r border-border p-2 text-xs text-white truncate ${
              rowIdx < timeline.length - 1 ? 'border-b border-border/30' : ''
            }`}>
              {item.name}
            </div>
            {Array.from({ length: totalWeeks }, (_, week) => {
              const isActive = week >= (item.start_week - 1) && week < item.end_week
              const isStart = week === (item.start_week - 1)
              const isEnd = week === (item.end_week - 1)

              return (
                <div
                  key={week}
                  className={`p-0.5 border-r border-border/20 ${
                    rowIdx < timeline.length - 1 ? 'border-b border-border/10' : ''
                  }`}
                >
                  {isActive && (
                    <div
                      className={`h-6 ${
                        item.effort === 'S' ? 'bg-emerald-500/50' :
                        item.effort === 'M' ? 'bg-accent/50' :
                        'bg-amber-500/50'
                      } ${isStart ? 'rounded-l-md' : ''} ${isEnd ? 'rounded-r-md' : ''}`}
                    />
                  )}
                </div>
              )
            })}
          </Fragment>
        ))}
      </div>

      {/* Legend */}
      <div className="flex gap-4 p-3 border-t border-border bg-surface/30">
        <div className="flex items-center gap-1.5 text-[10px] text-text-muted">
          <div className="w-3 h-3 rounded bg-emerald-500/50" /> Small (S)
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-text-muted">
          <div className="w-3 h-3 rounded bg-accent/50" /> Medium (M)
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-text-muted">
          <div className="w-3 h-3 rounded bg-amber-500/50" /> Large (L)
        </div>
      </div>
    </div>
  )
}
