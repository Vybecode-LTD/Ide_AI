/**
 * GuidedTour — The step-by-step onboarding walkthrough, rendered as a themed
 * glass-card overlay. Driven by `walkthroughStore` + `TOUR_STEPS`. Mounted once
 * globally for signed-in users (see App.tsx) and re-openable from `HelpButton`.
 *
 * Distinct from the ambient tutorial primitives (StageInterlude / PulseBeacon /
 * Whisper) — this is the explicit, linear "how it works" tour.
 */
import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useWalkthroughStore } from '../../stores/walkthroughStore'
import { TOUR_STEPS } from './tourSteps'
import { Button } from '../ui/Button'

export function GuidedTour() {
  const isOpen = useWalkthroughStore((s) => s.isOpen)
  const currentStep = useWalkthroughStore((s) => s.currentStep)
  const next = useWalkthroughStore((s) => s.next)
  const back = useWalkthroughStore((s) => s.back)
  const goToStep = useWalkthroughStore((s) => s.goToStep)
  const closeTour = useWalkthroughStore((s) => s.closeTour)
  const navigate = useNavigate()

  const step = TOUR_STEPS[currentStep]
  const isFirst = currentStep === 0
  const isLast = currentStep === TOUR_STEPS.length - 1

  // Keyboard navigation while the tour is open.
  useEffect(() => {
    if (!isOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeTour()
      else if (e.key === 'ArrowRight') next()
      else if (e.key === 'ArrowLeft') back()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isOpen, next, back, closeTour])

  /** Finish from the last step (and deep-link to the CTA route if set). */
  const finish = () => {
    closeTour()
    if (step?.route) navigate(step.route)
  }

  /** Jump to an intermediate step's screen, closing the tour. */
  const jumpTo = () => {
    if (!step?.route) return
    closeTour()
    navigate(step.route)
  }

  return (
    <AnimatePresence>
      {isOpen && step && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
        >
          {/* Backdrop — click to dismiss */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={closeTour}
            aria-hidden="true"
          />

          {/* Card */}
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby="guided-tour-title"
            className="relative z-10 w-full max-w-md rounded-[var(--radius-card)] border border-accent/20 bg-surface/90 backdrop-blur-xl p-6 md:p-7 shadow-[0_0_50px_rgba(0,229,255,0.12)]"
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.25 }}
          >
            {/* Close */}
            <button
              type="button"
              onClick={closeTour}
              aria-label="Close tutorial"
              className="absolute top-3 right-3 text-text-muted hover:text-white transition-colors text-lg leading-none"
            >
              ✕
            </button>

            <p className="text-[11px] uppercase tracking-wider text-accent/80 font-medium mb-3">
              Step {currentStep + 1} of {TOUR_STEPS.length}
            </p>

            <div className="text-3xl mb-3" aria-hidden="true">
              {step.emoji}
            </div>
            <h2 id="guided-tour-title" className="text-lg font-semibold text-white mb-2">
              {step.title}
            </h2>
            <p className="text-sm text-text-muted leading-relaxed mb-5">{step.body}</p>

            {/* Optional deep-link on intermediate steps */}
            {step.route && !isLast && (
              <button
                type="button"
                onClick={jumpTo}
                className="text-xs text-accent hover:text-accent/80 transition-colors mb-5 inline-flex items-center gap-1"
              >
                {step.routeLabel ?? 'Take me there'} →
              </button>
            )}

            {/* Progress dots */}
            <div className="flex items-center justify-center gap-1.5 mb-5">
              {TOUR_STEPS.map((s, i) => (
                <button
                  key={s.id}
                  type="button"
                  aria-label={`Go to step ${i + 1}`}
                  aria-current={i === currentStep}
                  onClick={() => goToStep(i)}
                  className={`h-1.5 rounded-full transition-all ${
                    i === currentStep ? 'w-5 bg-accent' : 'w-1.5 bg-white/20 hover:bg-white/40'
                  }`}
                />
              ))}
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between gap-2">
              {!isFirst ? (
                <Button variant="ghost" size="sm" onClick={back}>
                  ← Back
                </Button>
              ) : (
                <Button variant="ghost" size="sm" onClick={closeTour}>
                  Skip
                </Button>
              )}
              {isLast ? (
                <Button size="sm" onClick={finish}>
                  {step.routeLabel ?? 'Get started'}
                </Button>
              ) : (
                <Button size="sm" onClick={next}>
                  Next →
                </Button>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
