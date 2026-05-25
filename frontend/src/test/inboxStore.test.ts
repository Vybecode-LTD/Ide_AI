import { describe, it, expect, beforeEach } from 'vitest'
import { useInboxStore } from '../stores/inboxStore'

describe('inboxStore.adjust', () => {
  beforeEach(() => {
    useInboxStore.setState({ count: 0, streamConnected: false })
  })

  it('increments count', () => {
    useInboxStore.setState({ count: 5 })
    useInboxStore.getState().adjust(1)
    expect(useInboxStore.getState().count).toBe(6)
  })

  it('decrements count', () => {
    useInboxStore.setState({ count: 5 })
    useInboxStore.getState().adjust(-2)
    expect(useInboxStore.getState().count).toBe(3)
  })

  it('clamps at zero — never goes negative', () => {
    useInboxStore.setState({ count: 1 })
    useInboxStore.getState().adjust(-5)
    expect(useInboxStore.getState().count).toBe(0)
  })

  it('clamps at zero from zero', () => {
    useInboxStore.setState({ count: 0 })
    useInboxStore.getState().adjust(-1)
    expect(useInboxStore.getState().count).toBe(0)
  })

  it('handles large positive delta', () => {
    useInboxStore.setState({ count: 0 })
    useInboxStore.getState().adjust(100)
    expect(useInboxStore.getState().count).toBe(100)
  })
})
