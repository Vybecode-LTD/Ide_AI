import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ProgressPanel } from '../components/discovery/ProgressPanel'
import type { FieldSummary, FieldUpdate } from '../hooks/useSSE'

function makeSummary(modules: Array<{ id: string; label: string; filled: number; total: number; reqFilled: number; reqTotal: number }>): FieldSummary {
  const total_filled = modules.reduce((a, m) => a + m.filled, 0)
  const total_fields = modules.reduce((a, m) => a + m.total, 0)
  const required_filled = modules.reduce((a, m) => a + m.reqFilled, 0)
  const required_total = modules.reduce((a, m) => a + m.reqTotal, 0)
  return {
    total_filled,
    total_fields,
    required_filled,
    required_total,
    overall_percent: total_fields > 0 ? Math.round((total_filled / total_fields) * 100) : 0,
    per_module: modules.map((m) => ({
      module_id: m.id,
      label: m.label,
      filled: m.filled,
      total: m.total,
      required_filled: m.reqFilled,
      required_total: m.reqTotal,
    })),
  }
}

describe('ProgressPanel', () => {
  it('shows placeholder when summary is null', () => {
    render(<ProgressPanel summary={null} />)
    expect(screen.getByText(/send a message to see your progress/i)).toBeInTheDocument()
  })

  it('renders overall progress percentage', () => {
    const summary = makeSummary([
      { id: 'core', label: 'Core', filled: 3, total: 10, reqFilled: 2, reqTotal: 5 },
    ])
    render(<ProgressPanel summary={summary} />)
    expect(screen.getByText('30%')).toBeInTheDocument()
    expect(screen.getByText('3 of 10 fields')).toBeInTheDocument()
  })

  it('renders per-module counts', () => {
    const summary = makeSummary([
      { id: 'core', label: 'Core', filled: 2, total: 5, reqFilled: 1, reqTotal: 3 },
      { id: 'market', label: 'Market', filled: 1, total: 4, reqFilled: 0, reqTotal: 2 },
    ])
    render(<ProgressPanel summary={summary} />)
    expect(screen.getByText('2/5')).toBeInTheDocument()
    expect(screen.getByText('1/4')).toBeInTheDocument()
  })

  it('auto-expands module from recentUpdates', () => {
    const summary = makeSummary([
      { id: 'core', label: 'Core', filled: 2, total: 5, reqFilled: 1, reqTotal: 3 },
    ])
    const updates: FieldUpdate[] = [{ module_id: 'core', field_key: 'name', value: 'Test' }]
    render(<ProgressPanel summary={summary} recentUpdates={updates} />)
    expect(screen.getByText('+ Name')).toBeInTheDocument()
  })

  it('caps expanded modules at 3 (FIFO eviction)', () => {
    const summary = makeSummary([
      { id: 'a', label: 'Module A', filled: 1, total: 3, reqFilled: 1, reqTotal: 2 },
      { id: 'b', label: 'Module B', filled: 1, total: 3, reqFilled: 1, reqTotal: 2 },
      { id: 'c', label: 'Module C', filled: 1, total: 3, reqFilled: 1, reqTotal: 2 },
      { id: 'd', label: 'Module D', filled: 1, total: 3, reqFilled: 1, reqTotal: 2 },
    ])

    const { rerender } = render(
      <ProgressPanel
        summary={summary}
        recentUpdates={[{ module_id: 'a', field_key: 'f', value: 'v' }]}
      />,
    )

    // Module A is auto-expanded from recentUpdates
    const getExpandedCount = () =>
      screen.getAllByRole('button').filter((b) => b.getAttribute('aria-expanded') === 'true').length

    expect(getExpandedCount()).toBe(1)

    // Expand B, C, D via clicks
    const buttons = screen.getAllByRole('button')
    const bBtn = buttons.find((b) => b.textContent?.includes('Module B'))
    const cBtn = buttons.find((b) => b.textContent?.includes('Module C'))
    const dBtn = buttons.find((b) => b.textContent?.includes('Module D'))

    fireEvent.click(bBtn!)
    fireEvent.click(cBtn!)
    // After C, we have A + B + C = 3 (at cap)
    expect(getExpandedCount()).toBe(3)

    fireEvent.click(dBtn!)
    // After D, FIFO evicts the oldest — still capped at 3
    expect(getExpandedCount()).toBe(3)

    // Verify via rerender with new recentUpdate — still capped
    rerender(
      <ProgressPanel
        summary={summary}
        recentUpdates={[{ module_id: 'd', field_key: 'x', value: 'y' }]}
      />,
    )
    expect(getExpandedCount()).toBeLessThanOrEqual(3)
  })

  it('toggle collapses an expanded module', () => {
    const summary = makeSummary([
      { id: 'core', label: 'Core', filled: 2, total: 5, reqFilled: 1, reqTotal: 3 },
    ])
    const updates: FieldUpdate[] = [{ module_id: 'core', field_key: 'name', value: 'Test' }]
    render(<ProgressPanel summary={summary} recentUpdates={updates} />)

    const btn = screen.getByRole('button', { expanded: true })
    fireEvent.click(btn)
    expect(btn.getAttribute('aria-expanded')).toBe('false')
  })
})
