/**
 * HelpButton — Fixed "?" button in the top-right corner that (re)opens the
 * GuidedTour. Mounted globally for signed-in users (see App.tsx). Also fires
 * the one-time auto-launch of the tour for brand-new users.
 *
 * Note: on mobile, pages that render a TopBar show the Clerk avatar in the
 * top-right too. If that ever overlaps, nudge this button's position — it is
 * deliberately self-contained so layout tweaks stay local.
 */
import { useEffect } from 'react'
import { useWalkthroughStore } from '../../stores/walkthroughStore'

export function HelpButton() {
  const isOpen = useWalkthroughStore((s) => s.isOpen)
  const openTour = useWalkthroughStore((s) => s.openTour)

  // One-time auto-launch for first-time users (persisted flags gate re-runs).
  useEffect(() => {
    const s = useWalkthroughStore.getState()
    if (!s.autoLaunched && !s.completedTour) {
      s.openTour()
      s.markAutoLaunched()
    }
  }, [])

  // Hide the launcher while the tour itself is open.
  if (isOpen) return null

  return (
    <button
      type="button"
      onClick={openTour}
      aria-label="Open tutorial"
      title="How Ide/AI works"
      className="fixed top-3 right-3 z-40 flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface/80 text-sm font-semibold text-text-muted shadow-[0_0_20px_rgba(0,0,0,0.35)] backdrop-blur-md transition-all hover:border-accent/40 hover:text-accent"
    >
      ?
    </button>
  )
}
