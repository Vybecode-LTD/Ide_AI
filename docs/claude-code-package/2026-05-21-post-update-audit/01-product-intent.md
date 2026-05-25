# A. Product Intent

## What Ide/AI Is Trying To Achieve

Ide/AI is a pre-builder planning platform. Its job is to help a user decide what to build before they spend metered credits and development time inside tools such as Claude Code, Cursor, Bolt, Bubble, Replit, Lovable, Webflow, FlutterFlow, or similar builder environments.

The product promise is not "AI chat with a nicer UI." The product promise is a structured planning workspace that turns a rough idea into export-ready design artifacts.

## Core Problem

The user problem is that people often start building too early. They open a builder tool with a vague idea, spend credits and time discovering missing decisions, and produce unstable first drafts. Ide/AI is meant to move that decision-making into a dedicated preparatory workflow.

The intended result is that a user can enter a rough idea, answer guided questions, and leave with a package that can be handed to a builder tool or a human collaborator.

## Intended End-To-End Journey

1. User signs in with Clerk.
2. User starts from a rough idea, category, or project template.
3. User chooses or inherits an AI partner style.
4. User enters Discovery.
5. AI asks staged questions and extracts a structured design sheet in real time.
6. User leaves and returns without losing progress.
7. Library shows the real state of every project and sends users to the correct next step.
8. Once discovery has enough confidence, the project moves into modular pathway review.
9. User reviews a generated module pathway based on project category and concept sheet.
10. User locks the pathway and completes each module conversation.
11. System generates feature blocks, pipeline recommendations, market analysis, sprint plan, and prompt kits.
12. User exports design kits, prompt packages, transcripts, PDFs, DOCX files, or ZIP bundles.
13. User can share a public or private project brief and collect comments or ratings.
14. User can branch concepts, compare alternatives, merge the chosen direction, and preserve snapshots.
15. Billing and entitlements limit paid features cleanly without surprising failures.

## Major Product Surfaces

### Home And Templates

Home is the intake surface. It should let users quickly start with a blank idea or choose a prebuilt template. Category and template selection should produce a valid project with initial concept metadata and a design sheet when applicable.

Success criteria:

- Project creation is gated consistently by entitlement limits.
- Template-based creation respects the same project limits as blank creation.
- The selected category, partner, template, and initial idea carry forward into discovery and modular pathway generation.

### AI Discovery

Discovery is the central planning conversation. It must feel durable, structured, and recoverable.

Success criteria:

- Starting discovery on a project resumes the best existing active session by default.
- Leaving mid-session does not lose messages, stage, partner style, or sheet state.
- Auto-save does not overwrite server-canonical messages with stale client state.
- The design sheet hydrates on entry and updates during the stream.
- Existing projects affected by old empty-session creation can recover their older non-empty sessions.

### Library

Library is not just a list of projects. It is intended to be the user's project management cockpit.

Success criteria:

- Every project row shows useful progress metadata.
- Resume action routes to the next meaningful page.
- Snapshot create/list/restore works and preserves all design artifacts.
- `.ideai` import/export is reliable and obeys entitlements.
- Branch indicators and version counts are not cosmetic.

### Modular Pathway

The modular pathway turns a generic discovery sheet into a domain-specific design kit sequence. It is the layer that allows Ide/AI to serve software, marketing, brand, creative writing, events, education, food, fashion, finance, health, and other concept categories.

Success criteria:

- Categorization uses project description and design sheet fields.
- Assembly produces a coherent module list.
- Review lets users modify order and depth.
- Execution is resumable per module.
- Completing or skipping all modules marks the pathway complete in the backend.
- Library and sidebar read pathway progress from persisted backend state.

### Blocks, Pipeline, Prompt Kit, Market, And Sprints

These are the "make it buildable" surfaces.

Success criteria:

- Blocks are generated from the design sheet and user choices.
- Pipeline recommends tools, cost ranges, and compatibility notes.
- Prompt kits produce platform-specific instructions.
- Market analysis and sprint plans are gated by entitlement and recover gracefully from 403 errors.
- Export pages expose completed artifacts without duplicating stale version systems.

### Sharing And Feedback

Sharing turns a project into a stakeholder-facing brief.

Success criteria:

- Public shares are intentionally public.
- Password-protected shares actually protect all project-derived data, including comments and ratings.
- Feedback and ratings toggles behave consistently in backend and frontend.
- Public endpoints have spam, replay, and abuse controls appropriate for unauthenticated input.

### Billing And Entitlements

Billing is meant to make the product commercially viable. It should not be a cosmetic account badge.

Success criteria:

- Stripe checkout and portal work.
- Webhooks update local account type.
- Entitlement checks are centralized and consistent.
- Count-limited paid features count actual usage.
- Frontend displays upgrade paths instead of failing silently.

## Definition Of "Goal Achieved"

Ide/AI reaches the goal described in the product materials when:

- A user can complete the full idea-to-design-kit path without losing state.
- The Library page accurately tells them where to continue.
- Paid/free limits are enforced at every creation path.
- Public sharing does not bypass privacy settings.
- Exported artifacts contain enough detail to start work in a builder tool.
- Build, lint, and backend tests are part of the normal verification workflow.

