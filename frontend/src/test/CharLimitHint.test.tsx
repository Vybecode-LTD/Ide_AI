/**
 * CharLimitHint — quiet under the cap, a count near it, a clear message past it.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CharLimitHint } from '../components/ui/CharLimitHint'

const OVER = 'Over the 4,000-character limit. Shorten it to continue.'

describe('CharLimitHint', () => {
  it('shows nothing well under the cap', () => {
    const { container } = render(<CharLimitHint id="h" count={3199} max={4000} />)
    expect(container.textContent).toBe('')
  })

  it('shows a count from 80% of the cap', () => {
    render(<CharLimitHint id="h" count={3200} max={4000} />)
    expect(screen.getByText('3,200 / 4,000')).toBeInTheDocument()
    expect(screen.queryByText(OVER)).not.toBeInTheDocument()
  })

  it('allows exactly the cap without the over-limit message', () => {
    render(<CharLimitHint id="h" count={4000} max={4000} />)
    expect(screen.getByText('4,000 / 4,000')).toBeInTheDocument()
    expect(screen.queryByText(OVER)).not.toBeInTheDocument()
  })

  it('says so in a live region once over the cap', () => {
    render(<CharLimitHint id="h" count={4001} max={4000} />)
    const message = screen.getByText(OVER)
    expect(message).toHaveAttribute('aria-live', 'polite')
    expect(screen.getByText('4,001 / 4,000')).toBeInTheDocument()
  })

  it('carries the id the input points at', () => {
    const { container } = render(<CharLimitHint id="chat-limit" count={0} max={4000} />)
    expect(container.querySelector('#chat-limit')).not.toBeNull()
  })
})
