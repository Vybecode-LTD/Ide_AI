import { describe, it, expect } from 'vitest'
import { slugify } from '../lib/blogApi'

describe('slugify', () => {
  it('lowercases and hyphenates spaces', () => {
    expect(slugify('Hello World')).toBe('hello-world')
  })

  it('strips punctuation', () => {
    expect(slugify('Custom Slug!!')).toBe('custom-slug')
  })

  it('trims leading/trailing separators and whitespace', () => {
    expect(slugify('  Trim --- Me  ')).toBe('trim-me')
  })

  it('collapses non-alphanumerics (slashes, ampersands)', () => {
    expect(slugify('Ide/AI Tips & Tricks')).toBe('ide-ai-tips-tricks')
  })

  it('falls back to "post" for empty input', () => {
    expect(slugify('')).toBe('post')
    expect(slugify('!!!')).toBe('post')
  })
})
