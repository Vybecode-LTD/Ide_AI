/**
 * ProgressPanel — Module-aware progress meter for v2 Discovery.
 *
 * Replaces DesignSheetPanel on the right side of the Discovery page for v2
 * projects. Reads the latest `field_update` SSE payload to render an overall
 * completion ring, then an expandable per-module breakdown showing filled vs.
 * required-blank vs. optional-blank counts.
 *
 * Recently-filled keys (from the last SSE batch) get an accent flash so the
 * user can see exactly which fields the AI just extracted.
 *
 * @module components/discovery/ProgressPanel
 */
import { useEffect, useMemo, useState } from 'react'
import type { FieldSummary, FieldUpdate } from '../../hooks/useSSE'

/** Cap on simultaneously-expanded modules (FIFO eviction). Keeps the panel
 *  scannable on long sessions with many module updates. Manual user clicks
 *  follow the same cap. */
const MAX_AUTO_EXPANDED = 3

interface Props {
  summary: FieldSummary | null
  /** Most recent batch of field updates, used to flash "just filled" keys. */
  recentUpdates?: FieldUpdate[]
}

/** Format a snake_case or kebab-case identifier into a Title Case label. */
function titleize(s: string): string {
  return s
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function ProgressPanel({ summary, recentUpdates = [] }: Props) {
  // Track which modules are expanded — defaults to "all collapsed" with the
  // most-recently-updated module auto-expanded so the user sees what changed.
  const recentModuleId = recentUpdates[0]?.module_id ?? null
  const [expanded, setExpanded] = useState<Set<string>>(() =>
    recentModuleId ? new Set([recentModuleId]) : new Set(),
  )

  // Keep the most-recently-updated module auto-expanded. Cap auto-expanded
  // modules at MAX_AUTO_EXPANDED to keep the panel scannable on long sessions
  // — evicts the oldest entry FIFO. The user can still manually expand any
  // module by clicking its header (manual expansions follow the same FIFO).
  useEffect(() => {
    if (!recentModuleId) return
    queueMicrotask(() => {
      setExpanded((prev) => {
        if (prev.has(recentModuleId)) return prev
        const next = new Set(prev)
        next.add(recentModuleId)
        while (next.size > MAX_AUTO_EXPANDED) {
          const oldest = next.values().next().value
          if (!oldest) break
          next.delete(oldest)
        }
        return next
      })
    })
  }, [recentModuleId])

  // (module_id, field_key) tuples that were updated in the latest batch.
  const recentKeys = useMemo(() => {
    const set = new Set<string>()
    for (const u of recentUpdates) set.add(`${u.module_id}.${u.field_key}`)
    return set
  }, [recentUpdates])

  const toggle = (mid: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(mid)) {
        next.delete(mid)
      } else {
        next.add(mid)
        while (next.size > MAX_AUTO_EXPANDED) {
          const oldest = next.values().next().value
          if (!oldest) break
          next.delete(oldest)
        }
      }
      return next
    })

  if (!summary) {
    return (
      <div className="h-full overflow-y-auto p-3 md:p-4">
        <div className="text-xs text-text-muted italic">
          Send a message to see your progress. Each reply you give fills more
          design-kit fields automatically.
        </div>
      </div>
    )
  }

  const { overall_percent, required_filled, required_total, total_filled, total_fields, per_module } = summary
  const requiredPct = required_total > 0 ? Math.round((required_filled / required_total) * 100) : 0
  const requiredShort = required_total > 0 && requiredPct < 80

  return (
    <div className="h-full overflow-y-auto p-3 md:p-4 space-y-4">
      {/* Overall progress */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-text-muted font-medium">Design kit progress</span>
          <span className="text-sm font-bold text-accent" aria-live="polite">
            {overall_percent}%
          </span>
        </div>
        <div
          className="h-1.5 bg-white/5 rounded-full overflow-hidden"
          role="progressbar"
          aria-valuenow={overall_percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Overall design kit completion"
        >
          <div
            className="h-full bg-accent rounded-full transition-all duration-500"
            style={{ width: `${overall_percent}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2 text-[11px] text-text-muted">
          <span>
            {total_filled} of {total_fields} fields
          </span>
          <span className={requiredShort ? 'text-amber-300' : 'text-text-muted'}>
            {required_filled}/{required_total} required
          </span>
        </div>
      </div>

      {/* Per-module breakdown */}
      <div className="space-y-1.5">
        <span className="text-[10px] uppercase tracking-wider text-text-muted font-semibold">
          Modules
        </span>
        {per_module.length === 0 && (
          <p className="text-xs text-text-muted italic">No modules assembled.</p>
        )}
        {per_module.map((m) => {
          const isOpen = expanded.has(m.module_id)
          const isJustUpdated = m.module_id === recentModuleId
          const pct = m.total > 0 ? Math.round((m.filled / m.total) * 100) : 0
          const requiredBlank = Math.max(0, m.required_total - m.required_filled)
          const optionalBlank = Math.max(0, (m.total - m.required_total) - (m.filled - m.required_filled))
          return (
            <div
              key={m.module_id}
              className={`rounded-lg border transition-colors ${
                isJustUpdated
                  ? 'bg-accent/5 border-accent/40'
                  : 'bg-white/[0.02] border-border'
              }`}
            >
              <button
                type="button"
                onClick={() => toggle(m.module_id)}
                aria-expanded={isOpen}
                aria-controls={`module-detail-${m.module_id}`}
                className="w-full flex items-center gap-2 px-2.5 py-2 text-left hover:bg-white/[0.03] focus:outline-none focus:ring-1 focus:ring-accent/40 rounded-lg"
              >
                <span
                  className="text-xs text-text-muted shrink-0 w-3 text-center"
                  aria-hidden="true"
                >
                  {isOpen ? '▾' : '▸'}
                </span>
                <span className="text-xs text-white font-medium flex-1 capitalize truncate">
                  {titleize(m.label || m.module_id)}
                </span>
                <span
                  className={`text-[10px] font-semibold tabular-nums shrink-0 ${
                    pct >= 80 ? 'text-accent' : pct > 0 ? 'text-white/70' : 'text-text-muted'
                  }`}
                >
                  {m.filled}/{m.total}
                </span>
              </button>
              {isOpen && (
                <div
                  id={`module-detail-${m.module_id}`}
                  className="px-3 pb-2.5 pt-0.5 space-y-1.5"
                >
                  <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-1 text-[10px]">
                    <Stat label="Filled" value={m.filled} tone="accent" />
                    <Stat
                      label="Required left"
                      value={requiredBlank}
                      tone={requiredBlank > 0 ? 'warn' : 'muted'}
                    />
                    <Stat label="Optional left" value={optionalBlank} tone="muted" />
                  </div>
                  {/* Briefly highlight which keys were just filled */}
                  {Array.from(recentKeys)
                    .filter((k) => k.startsWith(`${m.module_id}.`))
                    .map((k) => (
                      <div
                        key={k}
                        className="text-[10px] text-accent/90 bg-accent/10 border border-accent/20 rounded px-1.5 py-0.5 inline-block mr-1"
                      >
                        + {titleize(k.split('.').slice(1).join('.'))}
                      </div>
                    ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface StatProps {
  label: string
  value: number
  tone: 'accent' | 'warn' | 'muted'
}

function Stat({ label, value, tone }: StatProps) {
  const toneClass =
    tone === 'accent' ? 'text-accent' : tone === 'warn' ? 'text-amber-300' : 'text-text-muted'
  return (
    <div className="bg-white/[0.03] rounded px-1.5 py-1">
      <div className={`font-bold tabular-nums ${toneClass}`}>{value}</div>
      <div className="text-text-muted/70 leading-tight">{label}</div>
    </div>
  )
}
