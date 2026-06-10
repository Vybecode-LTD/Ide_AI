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
import { useAuthStore } from '../../stores/authStore'
import { useWalkthroughStore } from '../../stores/walkthroughStore'

/** Accounts older than this never get the one-time tour auto-launch. */
const AUTO_LAUNCH_MAX_ACCOUNT_AGE_DAYS = 7

export function HelpButton() {
  const isOpen = useWalkthroughStore((s) => s.isOpen)
  const openTour = useWalkthroughStore((s) => s.openTour)
  const user = useAuthStore((s) => s.user)

  // One-time auto-launch for NEW signups only (persisted flags gate re-runs).
  // Waits for the backend profile so account age can gate it: existing users
  // get `autoLaunched` marked without the overlay popping — the "?" button
  // and Settings → "Replay Walkthrough" remain available to everyone.
  useEffect(() => {
    if (!user) {
      // Sidebar normally hydrates authStore, but not every signed-in page
      // renders one — fetch once so the age gate can evaluate everywhere.
      const auth = useAuthStore.getState()
      if (!auth.loading) void auth.fetchUser()
      return
    }
    const s = useWalkthroughStore.getState()
    if (s.autoLaunched || s.completedTour) return
    const ageMs = Date.now() - new Date(user.created_at).getTime()
    const isNewSignup =
      Number.isFinite(ageMs) && ageMs <= AUTO_LAUNCH_MAX_ACCOUNT_AGE_DAYS * 86_400_000
    if (isNewSignup) s.openTour()
    s.markAutoLaunched()
  }, [user])

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
