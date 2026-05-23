/**
 * Pipeline — Tech stack pipeline builder canvas.
 * @module pages/Pipeline
 */
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import apiClient from '../lib/apiClient'
import toast from 'react-hot-toast'
import { extractError } from '../lib/extractError'

interface PipelineNode {
  id: string
  layer: string
  selected_tool: string
  config?: { reason?: string }
}

interface CostEstimate {
  monthly_min: number
  monthly_max: number
  breakdown: Array<{ layer: string; tool: string; min: number; max: number }>
}

export function Pipeline() {
  const { projectId } = useParams<{ projectId: string }>()
  const [nodes, setNodes] = useState<PipelineNode[]>([])
  const [reasoning, setReasoning] = useState<string[]>([])
  const [cost, setCost] = useState<CostEstimate | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const [availableLayers, setAvailableLayers] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(false)
  const [recommending, setRecommending] = useState(false)

  const fetchPipeline = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const { data } = await apiClient.get(`/projects/${projectId}/pipeline`)
      setNodes(data.nodes || [])
      setCost(data.cost_estimate || null)
      setWarnings(data.warnings || [])
      setAvailableLayers(data.available_layers || {})
    } catch (err) {
      console.error('Failed to fetch pipeline:', err)
      toast.error(extractError(err, "Couldn't load pipeline."))
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { fetchPipeline() }, [fetchPipeline])

  const recommendPipeline = async () => {
    if (!projectId) return
    setRecommending(true)
    try {
      const { data } = await apiClient.post(`/projects/${projectId}/pipeline/recommend`)
      setNodes(data.nodes || [])
      setReasoning(data.reasoning || [])
      setCost(data.cost_estimate || null)
      setWarnings(data.warnings || [])
      setAvailableLayers(data.available_layers || {})
    } catch (err) {
      console.error('Failed to recommend pipeline:', err)
      toast.error(extractError(err, "Couldn't generate stack recommendation."))
    } finally {
      setRecommending(false)
    }
  }

  const updateLayer = async (layer: string, tool: string) => {
    // Optimistic update so the controlled <select> doesn't snap back
    setNodes(prev => prev.map(n => n.layer === layer ? { ...n, selected_tool: tool } : n))
    try {
      const { data } = await apiClient.patch(`/projects/${projectId}/pipeline/${layer}`, {
        selected_tool: tool,
      })
      // Reconcile with server response
      setNodes(prev => prev.map(n => n.layer === layer ? { ...n, selected_tool: data.selected_tool } : n))
    } catch (err) {
      console.error('Failed to update layer:', err)
      toast.error(extractError(err, "Couldn't update layer."))
      // Revert on failure by re-fetching
      fetchPipeline()
    }
  }

  const LAYER_LABELS: Record<string, string> = {
    frontend: 'Frontend', backend: 'Backend', database: 'Database',
    auth: 'Auth', hosting: 'Hosting', ai: 'AI',
  }

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar projectId={projectId} />
      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 flex flex-col h-dvh">
        <TopBar title="Pipeline Builder" subtitle="Select your tech stack">
          <Button variant="secondary" onClick={recommendPipeline} disabled={recommending}>
            {recommending ? 'Analyzing...' : 'AI Recommend'}
          </Button>
        </TopBar>

        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          {/* Pipeline Cards */}
          <div className="flex-1 p-4 md:p-6 overflow-y-auto">
            {loading ? (
              <div className="text-text-muted text-sm">Loading pipeline...</div>
            ) : nodes.length === 0 ? (
              <div className="text-center py-12 md:py-20">
                <p className="text-text-muted mb-4">No pipeline configured. Let AI recommend one.</p>
                <Button onClick={recommendPipeline} disabled={recommending}>Get AI Recommendation</Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pb-4">
                {nodes.map(node => (
                  <Card key={node.layer} className="flex flex-col gap-3" glow>
                    <h3 className="text-xs text-text-muted font-semibold uppercase tracking-wider">
                      {LAYER_LABELS[node.layer] || node.layer}
                    </h3>
                    <select
                      value={node.selected_tool}
                      onChange={(e) => updateLayer(node.layer, e.target.value)}
                      className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent"
                    >
                      {(availableLayers[node.layer] || [node.selected_tool]).map(tool => (
                        <option key={tool} value={tool}>{tool}</option>
                      ))}
                    </select>
                    {node.config?.reason && (
                      <p className="text-xs text-text-muted">{node.config.reason}</p>
                    )}
                  </Card>
                ))}
              </div>
            )}

            {warnings.length > 0 && (
              <div className="mt-4 md:mt-6 space-y-2">
                {warnings.map((w, i) => (
                  <div key={i} className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                    {w}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Cost Panel — stacks below on mobile, side panel on desktop */}
          <div className="w-full md:w-72 border-t md:border-t-0 md:border-l border-border bg-surface/30 shrink-0 p-4 overflow-y-auto">
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-4">Cost Estimate</h3>
            {cost ? (
              <>
                <div className="text-xl md:text-2xl font-bold text-white mb-1">
                  ${cost.monthly_min} &mdash; ${cost.monthly_max}
                </div>
                <p className="text-xs text-text-muted mb-4">per month</p>
                <div className="space-y-2">
                  {cost.breakdown?.map(item => (
                    <div key={item.layer} className="flex justify-between text-xs">
                      <span className="text-text-muted">{item.tool}</span>
                      <span className="text-white">${item.min}-${item.max}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-text-muted">Run AI recommendation to see costs.</p>
            )}

            {reasoning.length > 0 && (
              <div className="mt-6">
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Why This Stack</h4>
                <div className="space-y-2">
                  {reasoning.map((r, i) => (
                    <p key={i} className="text-xs text-text-muted">{r}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
