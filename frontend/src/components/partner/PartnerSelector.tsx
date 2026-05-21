/**
 * PartnerSelector — Modal overlay with a grid of AI Partner cards.
 * Fetches metadata from backend, renders PartnerCards, and emits selection.
 * @module components/partner/PartnerSelector
 */
import { useEffect, useState } from 'react'
import apiClient from '../../lib/apiClient'
import type { PartnerStyleMeta } from '../../types/project'
import { PartnerCard } from './PartnerCard'

interface Props {
  open: boolean
  currentStyle: string
  onSelect: (style: string) => void
  onClose: () => void
}

export function PartnerSelector({ open, currentStyle, onSelect, onClose }: Props) {
  const [styles, setStyles] = useState<PartnerStyleMeta[]>([])
  // Reset pending to currentStyle whenever the modal opens.
  const [pending, setPending] = useState(currentStyle)
  const [prevOpen, setPrevOpen] = useState(open)
  if (open && !prevOpen) {
    setPending(currentStyle)
  }
  if (open !== prevOpen) {
    setPrevOpen(open)
  }

  useEffect(() => {
    if (!open) return
    apiClient.get('/meta/partner-styles').then((r) => setStyles(r.data)).catch(() => {})
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-labelledby="partner-selector-title" aria-modal="true">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-0" onClick={onClose} />

      {/* Panel */}
      <div className="relative z-10 w-full max-w-2xl max-h-[85vh] rounded-2xl bg-surface border border-white/8 shadow-xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/8">
          <div>
            <h2 id="partner-selector-title" className="text-base font-semibold text-text-primary">Choose AI Partner</h2>
            <p className="text-xs text-text-muted mt-0.5">
              Pick a collaboration style — changes how the AI thinks with you, not what it produces.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/10 text-text-muted transition-colors"
            aria-label="Close"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {styles.map((s) => (
              <PartnerCard
                key={s.id}
                partner={s}
                selected={s.id === pending}
                onSelect={setPending}
              />
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-5 py-3.5 border-t border-white/8">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-text-muted rounded-lg hover:bg-white/5 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onSelect(pending)
              onClose()
            }}
            className="px-5 py-2 text-xs font-semibold rounded-lg bg-accent text-background hover:brightness-110 transition-all"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}
