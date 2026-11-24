/**
 * CharLimitHint — character counter for a length-capped text input.
 *
 * Empty while the text is well under its cap, a quiet count once it nears it,
 * and a red message once it is over (sending is blocked then). Give the input
 * `aria-describedby={id}`. Only the over-limit message is a live region, so a
 * screen reader hears it once rather than a count on every keystroke.
 * @module components/ui/CharLimitHint
 */
import { LIMIT_WARNING_RATIO } from '../../lib/inputLimits'

interface CharLimitHintProps {
  /** Referenced by the input's `aria-describedby`. */
  id: string
  /** Current length, from `charCount`. */
  count: number
  /** The cap, from `lib/inputLimits`. */
  max: number
  className?: string
}

const fmt = (n: number) => n.toLocaleString('en-US')

export function CharLimitHint({ id, count, max, className = '' }: CharLimitHintProps) {
  const over = count > max
  const near = count >= Math.ceil(max * LIMIT_WARNING_RATIO)

  return (
    <div id={id} className={`flex justify-between gap-3 text-xs ${className}`}>
      <span aria-live="polite" className="text-red-400">
        {over ? `Over the ${fmt(max)}-character limit. Shorten it to continue.` : ''}
      </span>
      {near && (
        <span className={`shrink-0 tabular-nums ${over ? 'text-red-400' : 'text-text-muted'}`}>
          {fmt(count)} / {fmt(max)}
        </span>
      )}
    </div>
  )
}
