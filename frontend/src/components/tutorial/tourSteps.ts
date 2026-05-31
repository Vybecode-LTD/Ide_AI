/**
 * tourSteps.ts — Content for the step-by-step Guided Tour (the linear
 * onboarding walkthrough). Pure data so it can be imported by both the
 * GuidedTour component and the walkthroughStore (one-way dependency).
 *
 * Keep copy benefit-oriented and jargon-light — the audience is a first-time
 * user who does not yet understand how Ide/AI works.
 */

export interface TourStep {
  /** Stable id (used for React keys + progress dots). */
  id: string
  /** Decorative emoji shown above the title (no asset dependency). */
  emoji: string
  title: string
  body: string
  /**
   * Optional deep-link target. On intermediate steps this renders a subtle
   * "take me there" affordance; on the final step it powers the primary CTA.
   */
  route?: string
  /** Label for the deep-link / final CTA button. */
  routeLabel?: string
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: 'welcome',
    emoji: '👋',
    title: 'Welcome to Ide/AI',
    body: 'Ide/AI turns a rough idea into a structured, export-ready design kit — before you spend a single credit in Bubble, Cursor, Bolt or Claude Code. This 60-second tour shows how the journey works.',
  },
  {
    id: 'idea',
    emoji: '💡',
    title: 'Start with your idea',
    body: 'On the Home screen, describe your idea in one box and pick a few options — your platform, audience, and the AI partner whose style matches how you like to think. That is all it takes to spin up a project.',
    route: '/home',
    routeLabel: 'Go to Home',
  },
  {
    id: 'discovery',
    emoji: '💬',
    title: 'AI-guided discovery',
    body: 'Your AI partner interviews you in a focused chat, drawing out the real problem, the audience, and the must-have features. Tap the suggested replies, or use the mic to talk instead of type — a live panel fills in your progress as you go.',
  },
  {
    id: 'design-kit',
    emoji: '🧩',
    title: 'Your design kit takes shape',
    body: 'As you chat, Ide/AI assembles a prioritized feature breakdown, a recommended tech stack, and a build pipeline — tailored to what you are actually making, whether that is an app, a film, or a coffee shop.',
  },
  {
    id: 'prompts',
    emoji: '⚙️',
    title: 'Platform-ready prompts',
    body: 'Get copy-paste prompt kits written in the exact format your builder expects — Bubble workflows, Claude Code schemas, Bolt one-shots and more. Prefer plain English? Flip on zero-jargon mode.',
  },
  {
    id: 'export',
    emoji: '📤',
    title: 'Export & push anywhere',
    body: 'Download everything as Markdown, PDF, DOCX or a ZIP — or push your whole design kit straight into a Notion page with one click. Your plan, ready to build.',
  },
  {
    id: 'ready',
    emoji: '🚀',
    title: "You're ready to build",
    body: 'That is the whole flow. You can reopen this tour any time from the “?” button in the top-right corner. Let us turn an idea into a plan.',
    route: '/home',
    routeLabel: 'Start building',
  },
]
