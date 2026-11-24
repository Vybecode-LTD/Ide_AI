/**
 * inputLimits — length caps on text the app sends to Claude.
 *
 * Mirrors `backend/app/core/limits.py`: the server rejects a longer value with
 * a 422, so the UI shows a counter and blocks sending first.
 * `backend/tests/test_input_length_caps.py` fails if the numbers here and
 * there disagree.
 * @module lib/inputLimits
 */

/** A discovery chat message or a module answer. */
export const CHAT_MESSAGE_MAX_CHARS = 4000

/** A project's idea description (the Home page also sends it for pathway detection). */
export const DESCRIPTION_MAX_CHARS = 10000

/** The counter appears once the text reaches this share of its cap. */
export const LIMIT_WARNING_RATIO = 0.8

/**
 * Length as the server counts it: Unicode code points (Python `len`), not
 * UTF-16 units (`String.length` counts an emoji as 2).
 */
export function charCount(text: string): number {
  return Array.from(text).length
}

/** True when `text` is longer than `max` characters as the server counts them. */
export function isOverLimit(text: string, max: number): boolean {
  return charCount(text) > max
}
