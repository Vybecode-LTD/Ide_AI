/**
 * Blocks — Drag-and-drop feature blocks board with scope slider.
 * @module pages/Blocks
 */
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import apiClient from '../lib/apiClient'

interface Block {
  id: string
  name: string
  description: string
  category: string
  priority: 'mvp' | 'v2'
  effort: 'S' | 'M' | 'L'
  order: number
  is_mvp: boolean
}

type Scope = 'lean' | 'balanced' | 'full'

const effortVariant = (e: string): 'success' | 'warning' | 'default' =>
  e === 'S' ? 'success' : e === 'M' ? 'warning' : 'default'

/* ── Sortable card ────────────────────────────────────────────── */
interface SortableBlockCardProps {
  block: Block
  onTogglePriority: (block: Block) => void
  onDelete: (id: string) => void
}

function SortableBlockCard({ block, onTogglePriority, onDelete }: SortableBlockCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: block.id,
  })

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 10 : 'auto',
  }

  return (
    <div ref={setNodeRef} style={style}>
      <Card className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2 flex-1 min-w-0">
            {/* Drag handle */}
            <button
              type="button"
              {...attributes}
              {...listeners}
              aria-label={`Drag ${block.name}`}
              className="cursor-grab active:cursor-grabbing text-text-muted hover:text-accent transition-colors p-1 -ml-1 shrink-0 touch-none"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
              </svg>
            </button>
            <h3 className="text-sm font-semibold text-white flex-1 min-w-0">{block.name}</h3>
          </div>
          <button
            type="button"
            onClick={() => onDelete(block.id)}
            aria-label={`Delete ${block.name}`}
            className="text-text-muted hover:text-red-400 text-xs shrink-0"
          >
            &#x2715;
          </button>
        </div>
        <p className="text-xs text-text-muted leading-relaxed">{block.description}</p>
        <div className="flex items-center gap-2 mt-auto flex-wrap">
          <button
            type="button"
            onClick={() => onTogglePriority(block)}
            aria-label={`Toggle priority for ${block.name}, currently ${block.priority}`}
          >
            <Badge variant={block.priority === 'mvp' ? 'accent' : 'default'}>
              {block.priority.toUpperCase()}
            </Badge>
          </button>
          <Badge variant={effortVariant(block.effort)}>{block.effort}</Badge>
          <Badge>{block.category}</Badge>
        </div>
      </Card>
    </div>
  )
}

/* ── Page ──────────────────────────────────────────────────────── */
export function Blocks() {
  const { projectId } = useParams<{ projectId: string }>()
  const [blocks, setBlocks] = useState<Block[]>([])
  const [scope, setScope] = useState<Scope>('balanced')
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 }, // Avoid accidental drags on click
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  )

  const fetchBlocks = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const { data } = await apiClient.get(`/projects/${projectId}/blocks`)
      setBlocks(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch blocks:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { fetchBlocks() }, [fetchBlocks])

  const generateBlocks = async () => {
    if (!projectId) return
    setGenerating(true)
    try {
      const { data } = await apiClient.post(`/projects/${projectId}/blocks/generate`)
      setBlocks(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to generate blocks:', err)
    } finally {
      setGenerating(false)
    }
  }

  const togglePriority = async (block: Block) => {
    const newPriority = block.priority === 'mvp' ? 'v2' : 'mvp'
    try {
      await apiClient.patch(`/projects/${projectId}/blocks/${block.id}`, {
        priority: newPriority,
        is_mvp: newPriority === 'mvp',
      })
      setBlocks((prev) =>
        prev.map((b) =>
          b.id === block.id ? { ...b, priority: newPriority, is_mvp: newPriority === 'mvp' } : b,
        ),
      )
    } catch (err) {
      console.error('Failed to update block:', err)
    }
  }

  const deleteBlock = async (blockId: string) => {
    try {
      await apiClient.delete(`/projects/${projectId}/blocks/${blockId}`)
      setBlocks((prev) => prev.filter((b) => b.id !== blockId))
    } catch (err) {
      console.error('Failed to delete block:', err)
    }
  }

  // Persist new order for any blocks whose position changed.
  const persistOrder = async (reordered: Block[]) => {
    if (!projectId) return
    const updates: Promise<unknown>[] = []
    reordered.forEach((b, idx) => {
      if (b.order !== idx) {
        updates.push(
          apiClient.patch(`/projects/${projectId}/blocks/${b.id}`, { order: idx }),
        )
      }
    })
    if (updates.length === 0) return
    try {
      await Promise.all(updates)
    } catch (err) {
      console.error('Failed to persist block order:', err)
      // Re-fetch to recover from any partial failures
      fetchBlocks()
    }
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    setBlocks((prev) => {
      const oldIndex = prev.findIndex((b) => b.id === active.id)
      const newIndex = prev.findIndex((b) => b.id === over.id)
      if (oldIndex === -1 || newIndex === -1) return prev
      const reordered = arrayMove(prev, oldIndex, newIndex)
      // Re-index `order` field locally so optimistic UI matches what we'll persist
      const reindexed = reordered.map((b, idx) => ({ ...b, order: idx }))
      // Fire-and-forget persistence
      persistOrder(reordered)
      return reindexed
    })
  }

  const filteredBlocks = blocks.filter((b) => {
    if (scope === 'lean') return b.priority === 'mvp' && b.effort !== 'L'
    if (scope === 'balanced') return b.priority === 'mvp'
    return true // full
  })

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar projectId={projectId} />
      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 flex flex-col h-dvh">
        <TopBar title="Design Blocks" subtitle={`${filteredBlocks.length} blocks shown`}>
          <Button variant="secondary" onClick={generateBlocks} disabled={generating}>
            {generating ? 'Generating...' : 'AI Generate'}
          </Button>
        </TopBar>

        <div className="p-4 md:p-6 flex-1 overflow-y-auto">
          {/* Scope Slider */}
          <div className="flex flex-wrap items-center gap-2 md:gap-4 mb-4 md:mb-6">
            <span className="text-xs text-text-muted font-medium">Scope:</span>
            {(['lean', 'balanced', 'full'] as Scope[]).map((s) => (
              <button
                key={s}
                onClick={() => setScope(s)}
                className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  scope === s
                    ? 'bg-accent text-background'
                    : 'bg-white/5 text-text-muted hover:text-white border border-border'
                }`}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
            {filteredBlocks.length > 1 && (
              <span className="text-[10px] text-text-muted/60 ml-auto hidden md:inline">
                Drag the handle to reorder
              </span>
            )}
          </div>

          {/* Blocks Grid */}
          {loading ? (
            <div className="text-text-muted text-sm">Loading blocks...</div>
          ) : filteredBlocks.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-text-muted mb-4">No blocks yet. Generate them from your design sheet.</p>
              <Button onClick={generateBlocks} disabled={generating}>Generate Blocks</Button>
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={filteredBlocks.map((b) => b.id)}
                strategy={rectSortingStrategy}
              >
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredBlocks.map((block) => (
                    <SortableBlockCard
                      key={block.id}
                      block={block}
                      onTogglePriority={togglePriority}
                      onDelete={deleteBlock}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          )}
        </div>
      </div>
    </div>
  )
}
