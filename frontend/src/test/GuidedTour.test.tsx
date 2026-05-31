import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { GuidedTour } from '../components/tutorial/GuidedTour'
import { useWalkthroughStore } from '../stores/walkthroughStore'
import { TOUR_STEPS } from '../components/tutorial/tourSteps'

function renderTour() {
  return render(
    <MemoryRouter>
      <GuidedTour />
    </MemoryRouter>,
  )
}

describe('GuidedTour', () => {
  beforeEach(() => {
    useWalkthroughStore.setState({
      isOpen: false,
      currentStep: 0,
      completedTour: false,
      autoLaunched: false,
    })
  })

  it('renders nothing when closed', () => {
    renderTour()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows the first step when open', () => {
    useWalkthroughStore.setState({ isOpen: true, currentStep: 0 })
    renderTour()
    expect(screen.getByText(TOUR_STEPS[0].title)).toBeInTheDocument()
    expect(screen.getByText(`Step 1 of ${TOUR_STEPS.length}`)).toBeInTheDocument()
  })

  it('advances to the next step when Next is clicked', () => {
    useWalkthroughStore.setState({ isOpen: true, currentStep: 0 })
    renderTour()
    fireEvent.click(screen.getByText(/Next/))
    expect(screen.getByText(TOUR_STEPS[1].title)).toBeInTheDocument()
  })

  it('closes and marks completed when Skip is clicked', () => {
    useWalkthroughStore.setState({ isOpen: true, currentStep: 0 })
    renderTour()
    fireEvent.click(screen.getByText('Skip'))
    expect(useWalkthroughStore.getState().isOpen).toBe(false)
    expect(useWalkthroughStore.getState().completedTour).toBe(true)
  })

  it('completes the tour from the final step CTA', () => {
    const last = TOUR_STEPS.length - 1
    useWalkthroughStore.setState({ isOpen: true, currentStep: last })
    renderTour()
    const label = TOUR_STEPS[last].routeLabel ?? 'Get started'
    fireEvent.click(screen.getByText(label))
    expect(useWalkthroughStore.getState().isOpen).toBe(false)
    expect(useWalkthroughStore.getState().completedTour).toBe(true)
  })
})
