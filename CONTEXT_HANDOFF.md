# Ide/AI — Context Handoff Document

> Use this file to get caught up on the current state of the project.
> Last updated: 2026-05-21

---

## What is Ide/AI?

Ide/AI takes a rough idea and turns it into a structured, export-ready design kit before the user opens a builder tool. The core problem: people waste credits, time, and money figuring out what to build inside metered platforms (Bubble, Cursor, Claude Code, Bolt, etc.) when that planning should happen beforehand.

The full process: describe an idea -> configure options -> AI-guided discovery conversation -> modular pathway -> walk away with a prioritized feature breakdown, tech stack recommendation, platform-specific prompts, and exportable docs.

**Live deployment:** Railway (backend + frontend as separate public services)

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL, Anthropic Claude API (claude-sonnet-4-6) |
| **Frontend** | React 19.2, TypeScript, Vite 7.3, Tailwind CSS v4 (CSS-based config), Framer Motion, Zustand |
| **Auth** | Clerk (Google/Microsoft/GitHub OAuth + email/password) |
| **Billing** | Stripe (checkout sessions, billing portal, webhook sync) |
| **Email** | Resend API — inbound email webhooks for Idea Inbox |
| **Deployment** | Railway (2 services), Docker, Caddy (frontend static) |
| **AI Streaming** | Server-Sent Events (SSE) for discovery chat, market analysis, module responses |
| **Export** | fpdf2 (PDF), python-docx (DOCX), Jinja2 templates, ZIP bundling |

---

## Recent Audit Work (2026-05-21)

A comprehensive codebase audit was completed covering P0 bugs, security hardening, and product completion. Key changes:

### P0 Fixes (Critical)
- **Discovery session resume** — `POST /discovery/start` is now idempotent; returns existing active session instead of always creating new ones. Added autosave on visibility change and unmount.
- **Inbox promotion crash** — Fixed `owner_id` -> `user_id` in project creation from inbox.
- **Branch creation crash** — Fixed `owner_id` -> `user_id` and added parent metadata copy.
- **ShareDialog routes** — Fixed 3 mismatched frontend routes (status/create/revoke).
- **Module session resume** — Active sessions return existing messages; complete sessions show transcript.

### Security Hardening
- **Sharing ownership checks** — Added `_verify_project_owner` to status/revoke endpoints.
- **Sprint ownership checks** — Added ownership verification to get/update/delete.
- **Sharing expiry enforcement** — Comments, ratings, CSV export now check share expiry.
- **JWT hardening** — Clerk issuer/audience/authorized-party validation (configurable via env vars).
- **Webhook HMAC** — Resend inbound email webhook now verifies HMAC signature.
- **Token encryption** — External integration tokens encrypted with Fernet.
- **Payload limits** — 256KB limit on inbound email webhook body.

### Product Completion
- **Library progress metadata** — Library listing now includes discovery_stage, design_confidence, block_count, pathway_status, and recommended_resume_path. Smart resume routing replaces hardcoded `/discovery/` links.
- **Snapshot unification** — Export page "Save Snapshot" now uses library snapshots API. `_gather_project_state` covers prompt kits, sprint plans, module pathways, and module responses.
- **Sharing feedback UI** — CommentSection, StarRating, FeedbackPanel components wired into SharedProject.tsx. Share response includes allow_feedback/allow_ratings flags.
- **Branching deep copy** — Branch creation deep-copies all child records (design sheet, sessions, blocks, pipeline, prompt kits, sprint plan, modules). Compare and merge endpoints added.
- **Prompt Kit page** — New `/prompts/:projectId` page with platform selector, generate, rewrite, copy, expand/collapse.
- **Integrations de-scoped** — Unconnected providers return `status: "coming_soon"`.
- **Billing entitlement** — `entitlement_service.py` with plan limits (free/basic/pro). Gates on project creation, prompt kit generation, and market analysis. `/auth/me/entitlements` endpoint.
- **Dependency upgrades** — All npm vulnerabilities resolved (Clerk, axios, vite, postcss, picomatch, etc.).
- **Rebrand** — All 4 pathway personas updated from ideaFORGE to Ide/AI. Settings page branding updated.

---

## Database Migrations (linear chain: 001-023)

| # | Description |
|---|-------------|
| 001-010 | Original schema through AI partner styles |
| 011 | Modular pathway system (categories, module_pathways, module_responses) |
| 012 | Email verification (legacy, now handled by Clerk) |
| 013 | User profile fields (account_type, bio) |
| 014 | Idea inbox |
| 015 | Sharing feedback + templates |
| 016 | Concept branches + external integrations |
| 017 | Seed project templates |
| 018 | Seed category templates |
| 019 | Add stripe_customer_id to users |
| 020 | Add password_resets table (legacy, now handled by Clerk) |
| 021 | Add clerk_user_id to users |
| 022 | Widen avatar_url column to TEXT |
| 023 | Deduplicate user rows (webhook cleanup) |

---

## Backend Routers

| Router | Purpose |
|--------|---------|
| `auth.py` | Clerk-based /me, avatar upload, profile updates, entitlements |
| `billing.py` | Stripe checkout, billing portal, webhook |
| `clerk_webhook.py` | Clerk user sync (create/update/delete) |
| `discovery.py` | SSE chat, greeting, partner switching (idempotent start) |
| `module_pathway.py` | Categorize, assemble, review, lock pathways |
| `modules.py` | Module start/respond/skip/summary (resumable) |
| `projects.py` | Project CRUD (with entitlement gate) |
| `pathways.py` | GET /pathways, POST /pathways/detect |
| `meta.py` | GET /meta/partner-styles |
| `blocks.py` | Feature blocks CRUD + generate |
| `pipeline.py` | Stack recommendation, UI skeleton |
| `prompts.py` | Prompt kit generate/rewrite (with entitlement gate) |
| `exports.py` | MD/PDF/DOCX/ZIP export + prompt packages |
| `market.py` | Market analysis SSE (with entitlement gate) |
| `sprints.py` | Sprint plan generation (with ownership checks) |
| `sharing.py` | Project sharing with ownership checks, expiry, comments + ratings |
| `library.py` | Library listing with progress metadata, .ideai export/import, snapshots |
| `inbox.py` | Idea inbox CRUD + build-to-project |
| `templates.py` | Seed templates |
| `branching.py` | Concept branching (deep copy, compare, merge) |
| `integrations.py` | External tool integrations (coming soon) |
| `webhooks.py` | Inbound email webhook (HMAC verified) |

---

## Frontend Pages

| Page | Route | Purpose |
|------|-------|---------|
| `Landing.tsx` | `/` (visitors) | Public landing, pricing |
| `SignInPage.tsx` | `/sign-in` | Clerk sign-in |
| `SignUpPage.tsx` | `/sign-up` | Clerk sign-up |
| `CheckoutRedirect.tsx` | `/checkout-redirect` | Stripe post-checkout |
| `Home.tsx` | `/home` | Idea input, partner grid, templates, project creation |
| `Discovery.tsx` | `/discovery/:projectId` | SSE chat with AI partner (autosave, resume) |
| `PathwayReview.tsx` | `/pathway-review/:projectId` | Module pathway review/reorder |
| `PathwayExecute.tsx` | `/pathway-execute/:projectId` | Module pathway execution |
| `ModuleSession.tsx` | `/module-session/:projectId/:moduleId` | Per-module AI conversation (resumable) |
| `Blocks.tsx` | `/blocks/:projectId` | Feature blocks board |
| `Pipeline.tsx` | `/pipeline/:projectId` | Stack recommendation canvas |
| `PromptKit.tsx` | `/prompts/:projectId` | Platform-specific prompt generation |
| `Exports.tsx` | `/exports/:projectId` | Export generation + prompt packages |
| `MarketAnalysis.tsx` | `/market/:projectId` | Competitive analysis |
| `SprintPlanner.tsx` | `/sprints/:projectId` | Sprint plan generation |
| `PitchMode.tsx` | `/pitch/:projectId` | Shareable one-page brief |
| `Profile.tsx` | `/profile` | Avatar, bio, stats, billing portal |
| `Inbox.tsx` | `/inbox` | Idea inbox |
| `Library.tsx` | `/library` | Project library with progress, snapshots, sharing |
| `Settings.tsx` | `/settings` | App settings, tutorial reset |
| `SharedProject.tsx` | `/shared/:token` | Public shared view with feedback |

---

## Zustand Stores

| Store | Purpose |
|-------|---------|
| `authStore.ts` | User state, fetchUser, updateUser, logout, initials |
| `modulePathwayStore.ts` | Module pathway state, assembled modules, responses |
| `tutorialStore.ts` | Ambient guidance tutorial dismissals (persisted to localStorage) |
| `pathwayStore.ts` | Concept pathway selection state |

---

## Environment Variables

### Backend (required)
- `DATABASE_URL` — PostgreSQL connection string
- `ANTHROPIC_API_KEY` — Claude API key
- `CLERK_SECRET_KEY` — Clerk backend secret
- `CLERK_WEBHOOK_SECRET` — Clerk webhook signing secret
- `STRIPE_SECRET_KEY` — Stripe backend secret
- `STRIPE_WEBHOOK_SECRET` — Stripe webhook signing secret
- `FRONTEND_URL` — Frontend origin for CORS/share links

### Backend (optional, security hardening)
- `CLERK_ISSUER` — Expected JWT issuer
- `CLERK_AUDIENCE` — Expected JWT audience
- `CLERK_AUTHORIZED_PARTIES` — Comma-separated allowed azp values
- `RESEND_WEBHOOK_SECRET` — HMAC key for Resend inbound email
- `INTEGRATION_TOKEN_KEY` — Fernet key for encrypting integration tokens

### Frontend
- `VITE_CLERK_PUBLISHABLE_KEY` — Clerk frontend key
- `VITE_API_BASE_URL` — Backend API base URL (defaults to `/api/v1`)
- `VITE_STRIPE_PUBLISHABLE_KEY` — Stripe frontend key

---

## Key Files for New Sessions

| Purpose | File |
|---------|------|
| Project instructions | `CLAUDE.md` |
| This handoff | `CONTEXT_HANDOFF.md` |
| AI partner spec | `AI_PARTNER_SELECTOR_SPEC.md` |
| Seed data (categories) | `backend/app/data/concept_categories.seed.json` |
| Seed data (modules) | `backend/app/data/module_library.seed.json` |
| Seed data (templates) | `project_templates.seed.json` |
| Audit roadmap | `docs/claude-code-package/2026-05-21-codebase-audit/README.md` |
| Clerk auth | `backend/app/core/clerk.py` |
| Stripe billing | `backend/app/routers/billing.py` |
| Entitlements | `backend/app/services/entitlement_service.py` |
