# A. What Ide/AI Is Attempting To Achieve

## Product Thesis

Ide/AI is a structured concept development workspace that sits before build tools. Its job is to reduce wasted time, builder credits, and implementation churn by helping users decide what to build before they paste prompts into metered or AI-assisted platforms.

The app is not meant to be a general chatbot. It is meant to be a guided planning system that turns a rough idea into a portable, export-ready design kit.

## Target Outcome

A successful user session should produce:

- a clear problem statement,
- a target audience,
- MVP scope,
- prioritized features,
- platform and tech-stack recommendations,
- pathway-specific design modules,
- prompt packages for AI builders,
- exportable documents and project history.

The intended session length is 15-30 minutes. That implies the app must behave like a durable workspace, not a transient chat page. A user should be able to leave discovery, return from the library, resume the same conversation, and keep advancing the same project state.

## Primary User Journey

1. User lands on Ide/AI and signs in with Clerk.
2. User selects a broad category and describes an idea.
3. User chooses an AI partner style such as Strategist, Skeptic, Coach, or Visionary.
4. App creates a project and starts discovery.
5. Discovery runs through AI-guided stages:
   - greeting,
   - problem,
   - audience,
   - features,
   - constraints,
   - confirm.
6. AI responses stream over SSE.
7. After conversation turns, backend extracts structured sheet fields into `design_sheets`.
8. User sees confidence increase in the right-hand design sheet panel.
9. When enough context exists, user proceeds to the modular pathway review.
10. App categorizes the concept and assembles a module path from a 47-module library.
11. User reviews, reorders, adds/removes modules, and toggles Lite/Deep.
12. User completes AI-guided modules or existing tool pages.
13. App generates downstream artifacts:
   - feature blocks,
   - tech pipeline,
   - prompt kit,
   - market analysis,
   - sprint plan,
   - pitch/export docs.
14. User exports a complete design kit or builder-specific prompt package.

## Core Product Pillars

### 1. Durable Project Workspace

Every project needs stable, resumable state:

- project metadata,
- discovery sessions,
- design sheet,
- generated blocks,
- pathway modules,
- module responses,
- exports,
- snapshots,
- library metadata.

The library is not just a list of projects. It should be the user's project management surface for opening active work, seeing progress, taking snapshots, exporting, branching, and restoring versions.

### 2. AI Partner Behavior

Partner selection is intended to change collaboration behavior, not only label or styling. The backend has partner style fragments and prompt composition to support this. The output schema must stay stable while the questioning style changes.

### 3. Structured Discovery

Discovery should be a state machine that uses conversation context and pathway stage definitions. The result is not just chat history; it is a structured design sheet that downstream modules can depend on.

### 4. Modular Design Kit Pathway

After discovery, Ide/AI should become adaptive. A software app, restaurant, fashion line, course, film, or social-impact project should receive a different module sequence.

The module system is intended to:

- categorize projects into 16 concept categories,
- assemble category-specific module stacks,
- enrich stacks based on discovery signals,
- let users edit and lock the pathway,
- collect module responses,
- cross-populate fields from earlier module outputs.

### 5. Builder-Ready Export

The final design kit should be usable outside Ide/AI. Target outputs include:

- Markdown,
- plain text,
- PDF,
- Word,
- ZIP,
- builder prompt packages for Claude Code, Cursor, Bolt, Lovable, Replit, ChatGPT, and generic tools.

### 6. Commercial SaaS Readiness

The codebase aims to support production SaaS basics:

- Clerk authentication,
- Stripe subscriptions,
- user profile and billing portal,
- inbound email ideas through Resend,
- project sharing,
- public shared project pages,
- Railway deployment.

## Definition Of Done For The Intended App

Ide/AI reaches its stated goal when:

- discovery can be interrupted and resumed without losing chat, stage, or sheet progress,
- library clearly shows project status and resumes the correct project workflow,
- generated artifacts are tied to the same durable project state,
- all advertised frontend actions call real backend endpoints,
- protected project-scoped APIs enforce ownership consistently,
- public sharing honors password, expiry, feedback, and rating settings,
- external integrations either work through real OAuth/push flows or are honestly marked as not implemented,
- tests cover the critical persistence and ownership paths,
- docs match the actual codebase.

