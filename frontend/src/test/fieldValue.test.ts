import { describe, expect, it } from 'vitest'
import { hasMeaningfulValue } from '../lib/fieldValue'

describe('hasMeaningfulValue', () => {
  it('rejects undefined and null', () => {
    expect(hasMeaningfulValue(undefined)).toBe(false)
    expect(hasMeaningfulValue(null)).toBe(false)
  })

  it('rejects empty and whitespace-only strings', () => {
    expect(hasMeaningfulValue('')).toBe(false)
    expect(hasMeaningfulValue('   ')).toBe(false)
    expect(hasMeaningfulValue('\t\n')).toBe(false)
  })

  it('accepts non-empty strings', () => {
    expect(hasMeaningfulValue('hello')).toBe(true)
    expect(hasMeaningfulValue(' a ')).toBe(true)
  })

  it('rejects empty arrays and objects', () => {
    expect(hasMeaningfulValue([])).toBe(false)
    expect(hasMeaningfulValue({})).toBe(false)
  })

  it('accepts non-empty arrays and objects', () => {
    expect(hasMeaningfulValue(['one'])).toBe(true)
    expect(hasMeaningfulValue({ key: 'value' })).toBe(true)
  })

  it('accepts numbers and booleans', () => {
    expect(hasMeaningfulValue(0)).toBe(true)
    expect(hasMeaningfulValue(42)).toBe(true)
    expect(hasMeaningfulValue(false)).toBe(true)
    expect(hasMeaningfulValue(true)).toBe(true)
  })
})
