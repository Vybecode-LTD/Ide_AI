/**
 * PitchMode — Clean pitch document with public sharing controls.
 * Includes a read-only React Flow user-flow diagram (4-6 nodes from MVP blocks).
 * @module pages/PitchMode
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import ReactFlow, {
  Background,
  Position,
  type Edge,
  type Node,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import apiClient from '../lib/apiClient'

interface SheetData {
  problem?: string
  audience?: string
  mvp?: string
  features?: Array<{ name: string; description?: string; priority?: string }>
  platform?: string
  tone?: string
  confidence_score?: number
}

interface Block {
  name: string
  description: string
  priority: string
}

/** Build a linear left-to-right flow: Start → Feature 1 → ... → Feature N → Done */
function buildFlow(blocks: Block[]): { nodes: Node[]; edges: Edge[] } {
  if (!blocks.length) return { nodes: [], edges: [] }

  // Cap at 6 for readability; minimum 1 will still produce 3 nodes (start + feature + end)
  const featureBlocks = blocks.slice(0, 6)
  const xGap = 200
  const yPos = 60

  const nodes: Node[] = [
    {
      id: 'start',
      position: { x: 0, y: yPos },
      data: { label: 'Start' },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: {
        background: 'rgba(0,229,255,0.15)',
        border: '1px solid rgba(0,229,255,0.6)',
        color: '#fff',
        borderRadius: 12,
        padding: '6px 12px',
        fontSize: 11,
        fontWeight: 600,
        width: 80,
        textAlign: 'center' as const,
      },
    },
    ...featureBlocks.map<Node>((b, i) => ({
      id: `f${i}`,
      position: { x: (i + 1) * xGap, y: yPos },
      data: { label: b.name },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: {
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.12)',
        color: '#fff',
        borderRadius: 12,
        padding: '6px 12px',
        fontSize: 11,
        fontWeight: 500,
        width: 160,
        textAlign: 'center' as const,
      },
    })),
    {
      id: 'done',
      position: { x: (featureBlocks.length + 1) * xGap, y: yPos },
      data: { label: 'Done' },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: {
        background: 'rgba(34,197,94,0.15)',
        border: '1px solid rgba(34,197,94,0.6)',
        color: '#fff',
        borderRadius: 12,
        padding: '6px 12px',
        fontSize: 11,
        fontWeight: 600,
        width: 80,
        textAlign: 'center' as const,
      },
    },
  ]

  // Linear edges Start → f0 → f1 → ... → done
  const edges: Edge[] = []
  const allIds = ['start', ...featureBlocks.map((_, i) => `f${i}`), 'done']
  for (let i = 0; i < allIds.length - 1; i++) {
    edges.push({
      id: `e-${allIds[i]}-${allIds[i + 1]}`,
      source: allIds[i],
      target: allIds[i + 1],
      animated: false,
      style: { stroke: 'rgba(0,229,255,0.45)', strokeWidth: 1.5 },
    })
  }

  return { nodes, edges }
}

export function PitchMode() {
  const { projectId } = useParams<{ projectId: string }>()
  const [sheet, setSheet] = useState<SheetData | null>(null)
  const [blocks, setBlocks] = useState<Block[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    if (!projectId) return
    try {
      const [sheetRes, blocksRes] = await Promise.all([
        apiClient.get(`/design-sheet/${projectId}`),
        apiClient.get(`/projects/${projectId}/blocks`),
      ])
      setSheet(sheetRes.data)
      const blocksArr = Array.isArray(blocksRes.data) ? blocksRes.data : []
      setBlocks(blocksArr.filter((b: { priority: string }) => b.priority === 'mvp').slice(0, 6))
    } catch (err) {
      console.error('Failed to load pitch data:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { fetchData() }, [fetchData])

  // Build the flow graph from the MVP blocks (memoized)
  const { nodes, edges } = useMemo(() => buildFlow(blocks), [blocks])

  const handlePrint = () => window.print()

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex">
        <Sidebar projectId={projectId} />
        <div className="ml-0 md:ml-[232px] flex-1 flex items-center justify-center">
          <p className="text-text-muted">Loading pitch...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar projectId={projectId} />
      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 flex flex-col h-dvh">
        <TopBar title="Pitch Mode" subtitle="Shareable project brief">
          <Button variant="secondary" onClick={handlePrint}>Print / PDF</Button>
        </TopBar>

        {/* Pitch Document */}
        <div className="flex-1 overflow-y-auto flex justify-center p-4 md:p-8 print:p-0">
          <article className="w-full max-w-3xl bg-surface border border-border rounded-xl p-5 md:p-10 print:border-none print:bg-white print:text-black">
            <h1 className="text-2xl md:text-3xl font-bold text-white print:text-black mb-2">
              Product Brief
            </h1>
            <div className="flex flex-wrap items-center gap-2 mb-6 md:mb-8">
              {sheet?.platform && <Badge variant="accent">{sheet.platform}</Badge>}
              {sheet?.confidence_score != null && (
                <Badge variant="success">{sheet.confidence_score}% confidence</Badge>
              )}
            </div>

            <section className="mb-8">
              <h2 className="text-sm font-semibold text-accent uppercase tracking-wider mb-2">Value Proposition</h2>
              <p className="text-white print:text-black leading-relaxed">{sheet?.problem || 'Not yet defined'}</p>
            </section>

            <section className="mb-8">
              <h2 className="text-sm font-semibold text-accent uppercase tracking-wider mb-2">Target Audience</h2>
              <p className="text-white print:text-black leading-relaxed">{sheet?.audience || 'Not yet defined'}</p>
            </section>

            <section className="mb-8">
              <h2 className="text-sm font-semibold text-accent uppercase tracking-wider mb-2">MVP Scope</h2>
              <p className="text-white print:text-black leading-relaxed">{sheet?.mvp || 'Not yet defined'}</p>
            </section>

            {/* User Flow Diagram — read-only, 4-6 nodes from MVP blocks */}
            {nodes.length > 0 && (
              <section className="mb-8">
                {/* Print overrides: ensure node fills/text/edges remain legible on paper */}
                <style>{`
                  @media print {
                    .pitch-flow-container .react-flow__node {
                      background: #f3f4f6 !important;
                      border: 1px solid #6b7280 !important;
                      color: #111827 !important;
                      -webkit-print-color-adjust: exact;
                      print-color-adjust: exact;
                    }
                    .pitch-flow-container .react-flow__edge-path {
                      stroke: #4b5563 !important;
                      stroke-width: 1.5 !important;
                    }
                    .pitch-flow-container .react-flow__background {
                      display: none !important;
                    }
                  }
                `}</style>
                <h2 className="text-sm font-semibold text-accent uppercase tracking-wider mb-3">User Flow</h2>
                <div
                  className="pitch-flow-container bg-background/40 border border-border rounded-lg overflow-hidden print:border-gray-300"
                  style={{ height: 180 }}
                  aria-label="User flow diagram showing MVP feature sequence"
                  role="img"
                >
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    fitView
                    fitViewOptions={{ padding: 0.15 }}
                    nodesDraggable={false}
                    nodesConnectable={false}
                    elementsSelectable={false}
                    zoomOnScroll={false}
                    zoomOnPinch={false}
                    panOnScroll={false}
                    panOnDrag={false}
                    preventScrolling={false}
                    proOptions={{ hideAttribution: true }}
                  >
                    <Background color="rgba(255,255,255,0.04)" gap={16} />
                  </ReactFlow>
                </div>
                <p className="text-[10px] text-text-muted/60 mt-2 print:text-gray-500">
                  Linear flow through {Math.min(blocks.length, 6)} MVP {blocks.length === 1 ? 'feature' : 'features'}.
                </p>
              </section>
            )}

            <section className="mb-8">
              <h2 className="text-sm font-semibold text-accent uppercase tracking-wider mb-2">Key Features</h2>
              <div className="space-y-3">
                {blocks.length > 0 ? blocks.map((b, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="w-6 h-6 rounded-full bg-accent/20 text-accent text-xs flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                    <div>
                      <h3 className="text-sm font-semibold text-white print:text-black">{b.name}</h3>
                      <p className="text-xs text-text-muted print:text-gray-600">{b.description}</p>
                    </div>
                  </div>
                )) : (
                  <p className="text-text-muted text-sm">Generate blocks to see features here.</p>
                )}
              </div>
            </section>

            <footer className="border-t border-border pt-4 mt-8">
              <p className="text-xs text-text-muted print:text-gray-400 italic">Generated by Ide/AI</p>
            </footer>
          </article>
        </div>
      </div>
    </div>
  )
}
