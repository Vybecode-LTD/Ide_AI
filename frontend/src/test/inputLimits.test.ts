/**
 * inputLimits — counts characters the way the server does.
 *
 * The backend caps are Python `len` (code points). `String.length` counts an
 * emoji as two, which would block a message the server accepts.
 */
import { describe, it, expect } from 'vitest'
import { CHAT_MESSAGE_MAX_CHARS, DESCRIPTION_MAX_CHARS, charCount, isOverLimit } from '../lib/inputLimits'

describe('inputLimits', () => {
  it('keeps the caps the owner chose', () => {
    expect(CHAT_MESSAGE_MAX_CHARS).toBe(4000)
    expect(DESCRIPTION_MAX_CHARS).toBe(10000)
  })

  it('counts an emoji as one character, like the server', () => {
    expect('🚀'.length).toBe(2)
    expect(charCount('🚀')).toBe(1)
    expect(charCount('a🚀b')).toBe(3)
  })

  it('allows exactly the cap and rejects one more', () => {
    expect(isOverLimit('x'.repeat(4000), 4000)).toBe(false)
    expect(isOverLimit('x'.repeat(4001), 4000)).toBe(true)
  })

  it('does not reject emoji text the server would accept', () => {
    const text = '🚀'.repeat(4000)
    expect(text.length).toBe(8000)
    expect(isOverLimit(text, 4000)).toBe(false)
  })
})
