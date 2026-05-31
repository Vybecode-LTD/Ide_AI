import { describe, it, expect, beforeEach } from 'vitest'
import { useWalkthroughStore } from '../stores/walkthroughStore'
import { TOUR_STEPS } from '../components/tutorial/tourSteps'

const LAST = TOUR_STEPS.length - 1

describe('walkthroughStore', () => {
  beforeEach(() => {
    useWalkthroughStore.setState({
      isOpen: false,
      currentStep: 0,
      completedTour: false,
      autoLaunched: false,
    })
  })

  it('openTour opens at the first step', () => {
    useWalkthroughStore.setState({ currentStep: 3 })
    useWalkthroughStore.getState().openTour()
    expect(useWalkthroughStore.getState().isOpen).toBe(true)
    expect(useWalkthroughStore.getState().currentStep).toBe(0)
  })

  it('next advances one step', () => {
    useWalkthroughStore.setState({ isOpen: true, currentStep: 0 })
    useWalkthroughStore.getState().next()
    expect(useWalkthroughStore.getState().currentStep).toBe(1)
  })

  it('next from the last step completes and closes the tour', () => {
    useWalkthroughStore.setState({ isOpen: true, currentStep: LAST })
    useWalkthroughStore.getState().next()
    const s = useWalkthroughStore.getState()
    expect(s.isOpen).toBe(false)
    expect(s.completedTour).toBe(true)
    expect(s.currentStep).toBe(0)
  })

  it('back clamps at zero', () => {
    useWalkthroughStore.setState({ currentStep: 0 })
    useWalkthroughStore.getState().back()
    expect(useWalkthroughStore.getState().currentStep).toBe(0)
  })

  it('back decrements from a middle step', () => {
    useWalkthroughStore.setState({ currentStep: 2 })
    useWalkthroughStore.getState().back()
    expect(useWalkthroughStore.getState().currentStep).toBe(1)
  })

  it('goToStep clamps within bounds', () => {
    useWalkthroughStore.getState().goToStep(999)
    expect(useWalkthroughStore.getState().currentStep).toBe(LAST)
    useWalkthroughStore.getState().goToStep(-5)
    expect(useWalkthroughStore.getState().currentStep).toBe(0)
  })

  it('closeTour marks the tour completed', () => {
    useWalkthroughStore.setState({ isOpen: true, completedTour: false })
    useWalkthroughStore.getState().closeTour()
    expect(useWalkthroughStore.getState().isOpen).toBe(false)
    expect(useWalkthroughStore.getState().completedTour).toBe(true)
  })

  it('markAutoLaunched sets the flag', () => {
    useWalkthroughStore.getState().markAutoLaunched()
    expect(useWalkthroughStore.getState().autoLaunched).toBe(true)
  })

  it('resetWalkthrough clears all flags so the tour can re-trigger', () => {
    useWalkthroughStore.setState({ completedTour: true, autoLaunched: true, currentStep: 4 })
    useWalkthroughStore.getState().resetWalkthrough()
    const s = useWalkthroughStore.getState()
    expect(s.completedTour).toBe(false)
    expect(s.autoLaunched).toBe(false)
    expect(s.currentStep).toBe(0)
    expect(s.isOpen).toBe(false)
  })
})
