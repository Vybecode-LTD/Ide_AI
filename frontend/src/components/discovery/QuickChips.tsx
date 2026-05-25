/**
 * QuickChips — Horizontal suggested reply chips.
 *
 * When the backend sends `__type_your_answer__` as a chip, it means the
 * question is open-ended and no preset answers are appropriate.  We render
 * a distinct amber "Type your answer below ↓" indicator instead.
 *
 * @module components/discovery/QuickChips
 */

/** Sentinel value matching `ai_service.CHIP_TYPE_YOUR_ANSWER` on the backend. */
const TYPE_YOUR_ANSWER_SENTINEL = '__type_your_answer__'

interface QuickChipsProps {
  chips: string[]
  onSelect: (chip: string) => void
  disabled?: boolean
}

export function QuickChips({ chips, onSelect, disabled }: QuickChipsProps) {
  if (!chips.length) return null

  // Filter out the sentinel — we handle it specially
  const regularChips = chips.filter((c) => c !== TYPE_YOUR_ANSWER_SENTINEL)
  const showTypeHint = chips.some((c) => c === TYPE_YOUR_ANSWER_SENTINEL)

  // If ONLY the sentinel is present, show just the type-hint
  // If regular chips exist alongside it, show both
  return (
    <div className="flex flex-wrap gap-1.5 md:gap-2 px-3 md:px-6 py-2 max-h-28 md:max-h-none overflow-y-auto overflow-x-hidden">
      {regularChips.map((chip, i) => (
        <button
          key={i}
          onClick={() => onSelect(chip)}
          disabled={disabled}
          aria-label={`Select: ${chip}`}
          className="px-2.5 md:px-3 py-2 md:py-1.5 min-h-[44px] md:min-h-0 rounded-full text-[11px] md:text-xs font-medium bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 focus:outline-none focus:ring-2 focus:ring-accent/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {chip}
        </button>
      ))}

      {showTypeHint && (
        <span
          role="status"
          className="px-2.5 md:px-3 py-2 md:py-1.5 min-h-[44px] md:min-h-0 rounded-full text-[11px] md:text-xs font-medium bg-amber-400/15 text-amber-300 border border-amber-400/25 select-none flex items-center gap-1"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="shrink-0" aria-hidden="true">
            <path d="M6 2v5M6 9v1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Type your answer below
        </span>
      )}
    </div>
  )
}
