/**
 * walkthroughStore.ts — Zustand store for the step-by-step Guided Tour, the
 * linear onboarding walkthrough that teaches new users how Ide/AI works.
 *
 * This is intentionally SEPARATE from `tutorialStore` (the ambient hints /
 * beacons / interludes). Only the durable flags (`completedTour`,
 * `autoLaunched`) are persisted — live UI state (`isOpen`, `currentStep`) is
 * not, so a page refresh never re-opens the overlay mid-session.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { TOUR_STEPS } from '../components/tutorial/tourSteps'

const LAST_STEP = TOUR_STEPS.length - 1

interface WalkthroughState {
  /** Overlay visibility (transient — not persisted). */
  isOpen: boolean
  /** Active step index (transient — not persisted). */
  currentStep: number
  /** User finished or skipped the tour at least once (persisted). */
  completedTour: boolean
  /** The one-time auto-launch has already fired for this user (persisted). */
  autoLaunched: boolean

  openTour: () => void
  closeTour: () => void
  next: () => void
  back: () => void
  goToStep: (step: number) => void
  markAutoLaunched: () => void
  resetWalkthrough: () => void
}

export const useWalkthroughStore = create<WalkthroughState>()(
  persist(
    (set, get) => ({
      isOpen: false,
      currentStep: 0,
      completedTour: false,
      autoLaunched: false,

      openTour: () => set({ isOpen: true, currentStep: 0 }),

      closeTour: () => set({ isOpen: false, completedTour: true }),

      next: () => {
        const { currentStep } = get()
        if (currentStep >= LAST_STEP) {
          // Finishing from the last step completes + closes the tour.
          set({ isOpen: false, completedTour: true, currentStep: 0 })
        } else {
          set({ currentStep: currentStep + 1 })
        }
      },

      back: () => set((s) => ({ currentStep: Math.max(0, s.currentStep - 1) })),

      goToStep: (step) =>
        set({ currentStep: Math.min(LAST_STEP, Math.max(0, step)) }),

      markAutoLaunched: () => set({ autoLaunched: true }),

      resetWalkthrough: () =>
        set({ isOpen: false, currentStep: 0, completedTour: false, autoLaunched: false }),
    }),
    {
      name: 'ideai-walkthrough',
      // Persist only the durable flags; never persist live overlay state.
      partialize: (s) => ({ completedTour: s.completedTour, autoLaunched: s.autoLaunched }),
    },
  ),
)
