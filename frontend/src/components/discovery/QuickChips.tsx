/**
 * QuickChips — Horizontal suggested reply chips.
 * @module components/discovery/QuickChips
 */

interface QuickChipsProps {
  chips: string[]
  onSelect: (chip: string) => void
  disabled?: boolean
}

export function QuickChips({ chips, onSelect, disabled }: QuickChipsProps) {
  if (!chips.length) return null

  return (
    <div className="flex flex-wrap gap-1.5 md:gap-2 px-3 md:px-6 py-2 max-h-28 md:max-h-none overflow-y-auto overflow-x-hidden">
      {chips.map((chip, i) => (
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
    </div>
  )
}
