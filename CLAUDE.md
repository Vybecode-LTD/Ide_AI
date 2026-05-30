# CLAUDE.md — Ide/AI

> **Version:** 2.12.0 · **Last updated:** 2026-05-30 · See [CHANGELOG.md](CHANGELOG.md)
>
> This file is the single source of truth for Claude Code sessions working on this project.
> Read this file first on every session start.
>
> 📋 **Documentation discipline is mandatory on this project.** Before declaring any code-touching task complete, run the checklist in the [Documentation Discipline](#documentation-discipline) section below. A Stop hook (`.claude/hooks/check-doc-versioning.sh`) will nag if you commit code without a CHANGELOG entry.

---

## Project Identity

- **Name:** Ide/AI (codebase directory: `Ide_AI`, formerly known as ideaFORGE)
- **Repo:** `github.com/PromptMonster-Media-Ltd/Ide_AI`
- **Working directory:** `C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\` — this is the ONLY working directory for this codebase. Any references in older docs to `D:\Development\Ide_AI\` or `D:\Development\ideaFORGE\` are obsolete.
- **Branch:** `main`
- **Deployment:** Railway (2 public services: backend + frontend, no reverse proxy)

---

## Documentation Discipline

**This project versions its documentation.** Read [DOC_VERSIONING.md](DOC_VERSIONING.md) for the full convention. The TL;DR for every code-touching session:

### Doc system scope — this project overrides the generic Claude-Kit

[DOC_VERSIONING.md](DOC_VERSIONING.md) is the **binding** documentation convention for Ide/AI: **root-level docs, SemVer _per doc_, one root [CHANGELOG.md](CHANGELOG.md), and the Stop hook.**

The parent `Development/CLAUDE.md` "Project Constitution" `@include`s a generic `DOCUMENTATION_MANAGER.md` describing a *different* system — a `docs/` managed-doc tree (`docs/BUGS.md`, `docs/HANDOFF.md`, `docs/AUDIT-LOG.md`, …), one **shared** version number across all docs, and `initialize project docs`. **That generic system does NOT apply here and must not be installed.** This project already tracks the same concerns in its root docs:

| Generic kit doc | Ide/AI equivalent (root-level) |
|---|---|
| `docs/ROADMAP.md` | [ROADMAP.md](ROADMAP.md) |
| `docs/CHANGELOG.md` | [CHANGELOG.md](CHANGELOG.md) |
| `docs/HANDOFF.md` | [CONTEXT_HANDOFF.md](CONTEXT_HANDOFF.md) |
| `docs/BUGS.md` | tracked in [TODO.md](TODO.md) + CHANGELOG `Fixed` entries |
| `docs/TESTING.md` | "Regression Test Matrix" in [CONTEXT_HANDOFF.md](CONTEXT_HANDOFF.md) |
| `docs/AUDIT-LOG.md` | not used — audit packages live under `docs/claude-code-package/` |

The `session-orchestrator` skill is installed **globally** and may be used for chronicling / reconciliation, **but it must operate on the root-level docs above — never create a `docs/` managed-doc tree, never impose a single shared version, never run `initialize project docs`.** The project-local [DOCUMENTATION_MANAGER.md](DOCUMENTATION_MANAGER.md) has been reconciled to match this mapping; the generic copies under `Development/` are unchanged and remain for other projects.

### End-of-session checklist (required)

Before declaring a task complete or committing, walk through this:

1. **Touched a feature listed in CLAUDE.md?** → Update that feature's description here, bump CLAUDE.md version.
2. **Touched a backend route, model, migration, or service?** → Reflect in CLAUDE.md Database Migrations / API Routes tables.
3. **User-visible behavior changed?** → Add a CHANGELOG.md entry under `[Unreleased]` (or today's date) with Added/Changed/Fixed/Security category.
4. **Resolved a TODO item?** → Move it to "Recently Done" in TODO.md.
5. **Session-defining work shipped?** → Update CONTEXT_HANDOFF.md "Current Session" with the commit refs.
6. **Bumped any versioned doc?** → Update its `Last updated` field to today's date.

### Versioned docs (frontmatter required)

These carry a `> **Version:** X.Y.Z · **Last updated:** YYYY-MM-DD · See [CHANGELOG.md](CHANGELOG.md)` line immediately after their H1:

- CLAUDE.md (this file)
- CONTEXT_HANDOFF.md
- TODO.md
- DOC_VERSIONING.md
- (CHANGELOG.md is append-only — no version on itself)

When you bump:
- **MAJOR** (X.0.0): restructure, new top-level section, content that contradicts previous version
- **MINOR** (X.Y.0): new content in existing section, new row in a table, new feature
- **PATCH** (X.Y.Z): typo, link fix, clarification

### Enforcement

- **Stop hook** at `.claude/hooks/check-doc-versioning.sh` fires when a session ends. If the latest commit touched `frontend/src/` or `backend/app/` files but didn't touch CHANGELOG.md, it prints a warning. **Non-blocking** — just a reminder.
- If you legitimately don't need a CHANGELOG entry (pure internal refactor, no doc impact), it's fine to ignore the nag. The hook errs on the side of reminding.
- The hook lives in `.claude/settings.json` under `hooks.Stop`. Don't disable it without proposing a replacement.

---

## What This Software Does

Ide/AI takes a rough idea and turns it into a structured, export-ready design kit before the user ever opens a builder tool. The core problem it solves: people waste credits, time, and money figuring out what to build inside metered platforms (Bubble, Cursor, Claude Code, Bolt, etc.) when that planning should happen beforehand in a purpose-built environment.

The full process takes 15–30 minutes: describe an idea, configure options, go through an AI-guided discovery conversation, and walk away with a prioritized feature breakdown, tech stack recommendation, platform-specific prompts, and exportable documentation.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL, Anthropic Claude API (claude-sonnet-4-6) |
| Frontend | React 19.2, TypeScript, Vite 7.3, Tailwind CSS v4 (CSS-based config, no tailwind.config.js), Framer Motion, Zustand |
| Auth | **Clerk** (Google/Microsoft/GitHub OAuth + email/password) — migrated from custom JWT |
| Billing | **Stripe** — checkout sessions, billing portal, webhook sync |
| Email | Resend API — inbound email webhooks for Idea Inbox |
| Deployment | Railway (2 services — backend + frontend exposed publicly), Docker |
| AI Streaming | Server-Sent Events (SSE) for discovery chat, market analysis, module responses |
| Export | fpdf2 (PDF), python-docx (DOCX), Jinja2 templates, ZIP bundling |

---

## Project Structure

```
C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, CORS, router registration
│   │   ├── core/
│   │   │   ├── config.py              # Settings from env vars (pydantic-settings)
│   │   │   ├── clerk.py               # Clerk JWT verification (JWKS/RS256)
│   │   │   └── database.py            # Async SQLAlchemy engine + session
│   │   │
│   │   ├── models/                    # SQLAlchemy ORM models (all UUID PKs)
│   │   │   ├── user.py                # User account (email/password + OAuth, email_verified, account_type, bio, inbox_email)
│   │   │   ├── project.py, session.py, design_sheet.py
│   │   │   ├── block.py, pipeline_node.py, prompt_kit.py
│   │   │   ├── market_analysis.py, sprint_plan.py, version.py, password_reset.py
│   │   │   ├── email_verification.py  # Legacy (now handled by Clerk)
│   │   │   ├── idea_inbox.py          # Inbound email → idea items
│   │   │   ├── project_share.py       # Sharing with feedback/ratings toggles
│   │   │   ├── share_comment.py       # Comments on shared projects
│   │   │   ├── share_rating.py        # Star ratings on shared project blocks
│   │   │   ├── project_template.py    # Seed template definitions
│   │   │   ├── concept_branch.py      # Git-like project forking
│   │   │   ├── external_integration.py # OAuth tokens for external tools
│   │   │   ├── module_pathway.py, module_response.py, module_artifact.py
│   │   │   ├── project_snapshot.py, user_memory.py
│   │   │   └── admin_audit_log.py     # Append-only admin action log
│   │   ├── schemas/                   # Pydantic v2 request/response schemas
│   │   ├── routers/                   # FastAPI route handlers
│   │   │   ├── admin.py               # Admin dashboard (user management, audit log)
│   │   │   ├── auth.py                # Clerk-based /me, avatar, profile, entitlements
│   │   │   ├── billing.py             # Stripe checkout, billing portal, webhook
│   │   │   ├── clerk_webhook.py       # Clerk user sync (create/update/delete)
│   │   │   ├── projects.py            # Project CRUD (with entitlement gate)
│   │   │   ├── discovery.py           # SSE chat, greeting, partner switching (idempotent start)
│   │   │   ├── meta.py                # GET /meta/partner-styles
│   │   │   ├── pathways.py            # GET /pathways, POST /pathways/detect (authenticated)
│   │   │   ├── blocks.py, pipeline.py, design_sheet.py, exports.py
│   │   │   ├── market.py              # Market analysis SSE (with entitlement gate)
│   │   │   ├── sprints.py             # Sprint plans (with ownership checks)
│   │   │   ├── sharing.py             # Project sharing with feedback/ratings, ownership checks
│   │   │   ├── library.py             # Library listing with progress metadata, snapshots, .ideai
│   │   │   ├── prompts.py             # Prompt kit generate/rewrite (with entitlement gate)
│   │   │   ├── inbox.py               # Idea inbox CRUD + build-to-project
│   │   │   ├── templates.py           # GET /templates (seed data)
│   │   │   ├── branching.py           # Concept branching (deep copy, compare, merge)
│   │   │   ├── integrations.py        # External tool integrations (coming_soon)
│   │   │   ├── webhooks.py            # Inbound email webhook (HMAC verified)
│   │   │   └── module_pathway.py, modules.py
│   │   ├── services/                  # Business logic
│   │   │   ├── ai_service.py          # build_system_prompt(), build_greeting_prompt(), stream_chat()
│   │   │   ├── artifact_context_service.py # Unified v1/v2 artifact bridge for downstream consumers
│   │   │   ├── audit_service.py       # Append-only admin audit log
│   │   │   ├── partner_style_service.py  # 10 AI partner styles, metadata, prompt fragments
│   │   │   ├── discovery_service.py   # Session management, stage progression, concept-sheet extraction
│   │   │   ├── pathway_service.py     # Concept Pathway registry (4 pathways)
│   │   │   ├── email_service.py       # Resend API: generic send helper
│   │   │   ├── sheet_service.py       # Design sheet CRUD + block generation
│   │   │   ├── pipeline_service.py    # Stack recommendation, cost estimation, compatibility
│   │   │   ├── export_service.py      # MD/PDF/DOCX/ZIP generation
│   │   │   ├── categorization_service.py, modular_pathway_service.py, module_service.py
│   │   │   ├── market_service.py, market_export_service.py, sprint_service.py
│   │   │   ├── prompt_kit_service.py, prompt_package_service.py
│   │   │   ├── entitlement_service.py  # Plan limits (free/basic/pro), feature gates
│   │   │   ├── inbox_pubsub.py        # Redis pub/sub for realtime inbox badge
│   │   │   └── sharing_service.py, library_service.py, memory_service.py, transcript_service.py
│   │   ├── alembic/versions/          # Database migrations (001–032, linear chain)
│   │   └── templates/                 # Jinja2 templates for prompts + exports
│   ├── tests/                         # 229 backend tests across 9 files
│   ├── pyproject.toml, Dockerfile, railway.toml
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Landing.tsx            # Public landing page with hero, features, pricing
│   │   │   ├── SignInPage.tsx         # Clerk sign-in
│   │   │   ├── SignUpPage.tsx         # Clerk sign-up
│   │   │   ├── CheckoutRedirect.tsx   # Stripe checkout redirect
│   │   │   ├── Home.tsx               # Idea input, partner grid, template grid, project creation
│   │   │   ├── CategorySelect.tsx     # Category selection for modular pathway
│   │   │   ├── Discovery.tsx          # SSE chat UI, partner badge, mid-session switching
│   │   │   ├── DesignKit.tsx          # v2 module responses viewer + editor + action cards
│   │   │   ├── Blocks.tsx             # Feature blocks board
│   │   │   ├── Pipeline.tsx, Exports.tsx, MarketAnalysis.tsx, SprintPlanner.tsx
│   │   │   ├── PromptKit.tsx          # Platform-specific prompt generation
│   │   │   ├── Profile.tsx            # Avatar upload, bio, stats, billing portal link
│   │   │   ├── Admin.tsx              # Admin dashboard (users, audit log)
│   │   │   ├── Inbox.tsx              # Idea inbox list, partner picker, build-to-project
│   │   │   ├── Library.tsx            # Project library with progress metadata, smart resume
│   │   │   ├── Settings.tsx           # App settings, tutorial reset, profile link
│   │   │   ├── SharedProject.tsx      # Public shared view with comments + ratings
│   │   │   ├── PrivacyPolicy.tsx, TermsOfService.tsx
│   │   │   ├── PathwayReview.tsx, PathwayExecute.tsx, ModuleSession.tsx
│   │   │   └── PitchMode.tsx
│   │   ├── components/
│   │   │   ├── admin/                 # AdminUserTable, AdminUserDrawer, AdminAuditList
│   │   │   ├── auth/ProtectedRoute.tsx # Clerk auth gate
│   │   │   ├── billing/               # CheckoutRedirect helpers
│   │   │   ├── layout/Sidebar.tsx     # Desktop sidebar + mobile bottom nav, profile container, inbox badge
│   │   │   ├── partner/               # PartnerCard, PartnerSelector, ActivePartnerBadge
│   │   │   ├── home/                  # PresetCard, TemplateGrid
│   │   │   ├── discovery/             # ChatBubble, TopBar, ProgressPanel, QuickChips
│   │   │   ├── framework/             # DesignSheetPanel, SheetCard, ReadinessScores
│   │   │   ├── pathway/               # Pathway selection and review components
│   │   │   ├── sharing/               # ShareDialog, CommentSection, StarRating, FeedbackPanel
│   │   │   ├── voice/                 # VoiceMicButton (Web Speech API toggle)
│   │   │   ├── tutorial/              # StageInterlude, PulseBeacon, Whisper
│   │   │   ├── nebula/                # Animated background canvas
│   │   │   └── ui/                    # Button, Modal, Card, Input, Badge, Drawer
│   │   ├── stores/                    # Zustand: authStore, pathwayStore, modulePathwayStore, tutorialStore, inboxStore, adminStore
│   │   ├── hooks/                     # useSSE, useVoiceInput
│   │   ├── lib/                       # apiClient.ts, authFetch.ts, fieldValue.ts, extractError.ts, plans.ts, categories.ts, exportUtils.ts
│   │   ├── types/                     # TypeScript interfaces (project, discovery, pathway, blocks, pipeline, export, modulePathway)
│   │   └── styles/                    # Tailwind v4 CSS globals
│   ├── vite.config.ts, tsconfig.json, Dockerfile, Caddyfile, railway.toml
├── project_templates.seed.json        # ~25 seed templates across 16 categories
├── docker-compose.yml
├── CLAUDE.md                          # THIS FILE
├── AI_PARTNER_SELECTOR_SPEC.md
├── ARCHITECTURE.md, PRD.md, FEATURE_SPEC.md
├── PRODUCT_DESCRIPTION.md, SYSTEM_PROMPT.md
├── CONTEXT_HANDOFF.md, DEPLOYMENT_RAILWAY.md, PROMPT_SEQUENCE.md
```

---

## Features

### 1. Authentication & User Management (Clerk)
- **Clerk-managed** sign-in/sign-up (email/password + Google, Microsoft, GitHub OAuth)
- Clerk webhook syncs users to local DB (`clerk_webhook.py`)
- Backend verifies Clerk session JWTs via JWKS (`core/clerk.py`)
- Frontend uses `@clerk/clerk-react` — `SignInPage.tsx`, `SignUpPage.tsx`
- `ProtectedRoute` uses Clerk's `useAuth()` hook
- `apiClient.ts` attaches Clerk session token via `getToken()`
- Avatar upload (JPEG/PNG/WebP, max 2MB, stored as base64 data URI)
- Per-user persistent memory injected into AI context
- Endpoints: `GET /auth/me`, `PATCH /auth/me`, `POST /auth/me/avatar`, `GET /auth/me/entitlements`

### 1b. Stripe Billing + Entitlements
- Checkout sessions for subscription plans (Basic Monthly/Yearly, Pro Monthly/Yearly)
- Billing portal for managing subscriptions
- Stripe webhook syncs customer ID and subscription status
- `CheckoutRedirect.tsx` handles post-checkout flow
- `Profile.tsx` has "Manage Billing" button
- `Landing.tsx` has pricing section with Upgrade buttons
- Entitlement service: plan-based limits (free: 3 projects / basic: 25 / pro: unlimited)
- Feature gates on project creation, prompt kit generation, and market analysis
- Endpoints: `POST /billing/checkout`, `POST /billing/portal`, `POST /billing/webhook`
- DB: `stripe_customer_id` on users (migration 019), subscription state columns (migration 032)

### 2. Project System
- Single text input for idea description
- Configuration selectors: platform, audience, complexity, tone, pathway, AI partner style
- Platform options: Bubble, Webflow, FlutterFlow, Bolt, Lovable, Claude Code, Cursor, Replit, n8n, Custom
- Audience options: Consumers, Businesses, Internal Team, Developers
- Complexity: Simple (1–5 screens), Medium (5–15), Complex (15+)
- Tone: Formal, Casual, Technical, Startup-style
- Snapshot-based version history (JSONB), auto-saves at milestones, restore any version
- Multi-user project sharing with feedback/ratings
- Template-based creation from ~25 seed templates across 16 categories
- DB: `projects` table — UUID PK, user_id FK, name, accent color, platform, pathway_id, ai_partner_style

### 3. Concept Pathways
- Domain-specific project types that customize the entire discovery experience
- 4 pathways: Software Product (default), Marketing Campaign, Brand Identity, Creative Writing
- Each pathway defines: base_persona, discovery_stages (divergent/convergent), sheet_schema, creation_fields, creation_presets
- AI auto-detection: `POST /pathways/detect` analyzes idea and recommends pathway
- Registry: `backend/app/services/pathway_service.py`, served via `GET /pathways`
- DB: `pathway_id` column on projects (migration 009)

### 4. AI Partner Selector
- 10 collaboration styles that change actual AI behavior (not cosmetic)
- Partners: Creative, Intellectual, Trailblazer, Strategist (DEFAULT), Architect, Coach, Skeptic, Visionary, Editor, Scientist
- 3-layer prompt composition: (1) Base pathway persona → (2) Partner style fragment → (3) Session context
- Each fragment has Core Behaviour, Questioning Style, and Guardrails sections
- Partners change HOW the AI collaborates — structured output schema is NEVER altered by partner choice
- Mid-session switching: `PATCH /discovery/{session_id}/partner` — preserves chat + sheet, applies to future replies only
- Metadata: `GET /meta/partner-styles` — frontend fetches from backend, never hardcoded
- Home page: inline 5x2 glassmorphism preset grid (not a modal)
- Discovery page: ActivePartnerBadge in header, PartnerSelector modal for mid-session switch
- DB: `ai_partner_style` on projects + sessions (migration 010)

### 5. AI Discovery Chat
- SSE streaming via FastAPI StreamingResponse + EventSource on frontend
- **Branches on `project.flow_version`**:
  - **v1 (legacy projects)**: State machine stages (greeting → problem → audience → features → constraints → confirm). After each AI response the backend extracts design-sheet fields, writes to `design_sheets`, emits `sheet_update` event. This is the original behavior — untouched.
  - **v2 (new projects)**: Unified prompt that targets ALL module field schemas at once. The AI sees every assembled module + its fields + what's already filled, and funnels toward the first unfilled REQUIRED field each turn. After each response the backend runs `extract_module_fields` and writes per-module field values into `module_responses.responses`. Emits a `field_update` SSE event containing per-field updates + an aggregate summary (overall %, required %, per-module breakdown).
- Event types: `token` (streaming text), `sheet_update` (v1 only), `field_update` (v2 only), `done` (response complete; always emitted, hardened with try/except + fallback chips)
- Quick reply chips: AI-generated suggested replies per turn (`[CHIPS: a | b | c]` extracted with 3-stage fallback chain)
- Voice input: Web Speech API mic button next to chat input (browser-only, zero backend cost)
- UI: left stage stepper, center chat thread, right side panel branches on `flow_version`:
  - **v1**: `DesignSheetPanel` (`components/framework/DesignSheetPanel.tsx`) showing extracted design-sheet fields + confidence ring
  - **v2**: `ProgressPanel` (`components/discovery/ProgressPanel.tsx`) showing overall %, expandable per-module breakdown with filled/required-left/optional-left counts, accent highlight on just-filled fields
- Proceed button gate also branches:
  - **v1**: appears when `sheet.confidence_score >= 70`, routes to `/pathway-review/{id}`
  - **v2**: always available once `summary.required_total > 0`, routes to `/exports/{id}` (interim Design Kit destination — Phase 5 swaps to `/design-kit/{id}`). Warning chip shows live `required_filled / required_total` percentage when below 80%.
- `useSSE` hook accepts `onFieldUpdate` callback alongside `onSheetUpdate` — exports `FieldUpdate`, `FieldSummary`, `FieldUpdatePayload` types
- v2 greeting uses a dedicated `build_unified_greeting_prompt` that references the assembled modules + steers toward the first required field's extraction hint. v1 keeps the legacy `build_greeting_prompt`.
- v2 ProgressPanel hydrates on mount via `GET /discovery/{session_id}/field-summary` so resume mid-session shows accurate progress without waiting for the next message.
- v2 Discovery hides the stage UI (TopBar subtitle, left StagesStepper, mobile stage indicator) — the unified flow has no stage progression.
- AI model: Anthropic Claude (claude-sonnet-4-6), configurable via CLAUDE_MODEL env var
- Designed for 15–30 minute sessions from idea to completed design kit

### 6. Design Sheet
- Structured data auto-populated from discovery conversation in real time
- Fields: problem, audience, MVP scope, features (JSONB), tone, platform, constraints, plus pathway-specific fields
- Updated via sheet_update SSE events, frontend syncs via Zustand store
- DB: `design_sheets` table

### 7. Design Blocks Board
- AI generates 8–12 feature cards from completed design sheet
- Card properties: title, description, category, priority (MVP/V2), effort (S/M/L), sort order
- Drag-and-drop via @dnd-kit/core
- Scope slider: Lean / Balanced / Full filters visible blocks
- Right panel: Prompt Kit Preview showing how blocks translate to platform prompts
- Actions: regenerate blocks, add custom block
- DB: `blocks` table

### 8. Pipeline Builder
- 7 infrastructure layers: Frontend, Backend, Database, Automations, AI/Agents, Analytics, Deployment
- AI recommends tools per layer based on project requirements
- Curated tool options per layer with cost/complexity metadata
- Cost estimation: min/max USD/month range
- Compatibility checking with notes on tool interplay
- Swap any tool → AI re-evaluates compatibility
- UI skeleton generation: JSON screen list + nav flow + component inventory
- UI: horizontal scrollable canvas, SVG connector lines, right cost/compatibility panel
- DB: `pipeline_nodes` table

### 9. Prompt Kit Generator
- Structured, copyable prompt blocks formatted for the user's specific builder platform
- Sections: System Context, App Description, Feature List, Data Model, Constraints, First Task
- 7 platform templates (Jinja2) — each written in that platform's expected format/terminology:
  - Bubble: data type definitions + workflow instructions
  - Claude Code: database schemas, API endpoints, phased implementation plan
  - Bolt: single paste-ready prompt + follow-up prompts for iteration
  - + Webflow, FlutterFlow, Cursor, Replit
- Zero Dev Language Mode: rewrites prompts in jargon-free plain language
- Actions: copy all, copy section, regenerate
- DB: `prompt_kits` table

### 10. Market Analysis
- AI-driven competitive analysis, streamed via SSE
- Endpoint: `POST /market/{project_id}/generate`
- DB: `market_analyses` table (migration 002)

### 11. Sprint Planner
- Auto-generated development sprint plans from design sheet + feature blocks
- Ownership verification on get/update/delete
- Endpoint: `POST /sprints/{project_id}/generate`
- DB: `sprint_plans` table (migrations 007, 008)

### 12. Pitch Mode
- Clean, shareable one-page project brief
- Content: title, value proposition, audience, features (3–5), MVP scope, flow diagram
- Flow diagram: React Flow (read-only), 4–6 nodes from blocks
- Sharing: toggle public link, copy URL, set expiry
- Export: print/PDF via browser print API

### 13. Export System
- Formats: Markdown (.md), plain text (.txt), PDF (.pdf), Word (.docx), ZIP (all formats)
- Platform-specific Jinja2 templates
- Market analysis export: PDF, DOCX, TXT via `GET /market/{id}/export?format=pdf|docx|txt`
- Endpoint: `GET /projects/{id}/export?format=md|pdf|docx|zip`

### 14. Modular Dynamic Design Kit Pathway
- AI categorizes projects into 16 concept categories (software, food, film, fashion, etc.)
- Each category has a unique default module set drawn from a library of 40 modules
- Categorization uses project name + description + concept sheet fields for accurate classification
- Pathway assembly: base stack (from category) → enrichment pass (signals from concept sheet) → user review
- Users can reorder, add/remove modules, toggle Lite (2–3 questions) / Deep (6–10 questions) per module
- Cross-module intelligence: 7 field mapping rules pre-populate answers from earlier modules
- SSE-streamed AI conversations per module with `[MODULE_COMPLETE]` and `[CHIPS:]` markers
- Seed data: `concept_categories.seed.json` (16 categories), `module_library.seed.json` (47 modules)
- Backend: `categorization_service.py`, `modular_pathway_service.py`, `module_service.py`
- Routers: `module_pathway.py` (categorize/assemble/review/lock), `modules.py` (start/respond/skip/summary)
- Frontend: `PathwayReview.tsx`, `PathwayExecute.tsx`, `ModuleSession.tsx`, `modulePathwayStore.ts`
- DB: `module_pathways` table, `module_responses` table (migration 011)

### 15. Ambient Guidance Tutorial System
- Three components: StageInterlude (phase transition cards), PulseBeacon (attention rings), Whisper (contextual tips)
- Integrated into 7 pages: Home, Discovery, PathwayReview, PathwayExecute, ModuleSession, Exports, Settings
- Dismissals persisted via Zustand + localStorage (`ideaforge-tutorial` key)
- Reset button in Settings page clears all tutorial state
- Components: `frontend/src/components/tutorial/` (StageInterlude, PulseBeacon, Whisper)
- Store: `frontend/src/stores/tutorialStore.ts`

### 16. Project Folder System
- Persistent sidebar folder tree
- Sections per project: Discovery Notes, Design Sheet, Prompt Kit, Pipeline Map, Exports, Versions
- Version timeline dots, click to restore any snapshot
- Actions: New Project, Duplicate, Archive

### 17. Email Verification (Legacy — now handled by Clerk)
- Previously used custom 6-digit codes via Resend API
- Now handled entirely by Clerk's built-in email verification
- DB tables (`email_verifications`, `password_resets`) still exist but are unused
- Migrations 012, 020 created these tables — kept for migration chain integrity

### 18. User Profiles
- Dedicated profile page (`/profile`) with avatar upload, bio editor, project stats
- Avatar: uploaded image (JPEG/PNG/WebP, max 2MB) or generated initials fallback
- Account type badge (free/pro)
- Sidebar profile container: avatar circle, display name, plan badge, link to profile
- Centralized `authStore` (Zustand) — `user`, `fetchUser()`, `updateUser()`, `logout()`, `initials()`
- Backend: `POST /auth/me/avatar`, `PATCH /auth/me` for profile updates
- DB: `account_type`, `bio` columns (migration 013)

### 19. Idea Inbox
- Email-to-idea pipeline: users get a unique `inbox_email` address
- Inbound emails parsed via Resend webhook → `IdeaInboxItem` records
- Manual idea capture also supported
- Per-item: choose AI partner style, promote to full project ("Build"), or delete
- Sidebar shows unread inbox count badge — updated in realtime via SSE stream (Redis pub/sub backed). Falls back to a one-shot fetch on mount when Redis isn't configured (`REDIS_URL` empty → endpoint returns 503).
- Realtime architecture: `app/services/inbox_pubsub.py` publishes to `inbox:user:{user_id}` channel on every mutation; `GET /inbox/stream` opens an SSE subscription for the authenticated user and pushes `hello` (initial count) + `update` events as they happen
- Endpoints: `GET /inbox`, `POST /inbox`, `GET /inbox/count`, `GET /inbox/stream` (SSE), `POST /inbox/{id}/promote`, `DELETE /inbox/{id}`
- Webhook: `POST /webhooks/inbound-email` (publishes to pubsub after creating the row)
- Frontend: `inboxStore` (Zustand) manages connection + auto-reconnect with exponential backoff; Sidebar wires `connectStream()` / `disconnectStream()` to mount/unmount
- DB: `idea_inbox_items` table, `inbox_email` on users (migration 014)
- Required env var (production): `REDIS_URL` — without it, the stream returns 503 and the frontend falls back to mount-time fetches only

### 20. Sharing Feedback & Ratings
- Project shares can enable comments and/or star ratings via toggles
- Viewers can leave threaded comments and rate individual feature blocks (1–5 stars)
- Owner sees aggregated feedback in a FeedbackPanel
- ShareDialog has "Allow Comments" and "Allow Feature Ratings" toggles
- Endpoints: `POST/GET /sharing/public/{token}/comments`, `POST/GET /sharing/public/{token}/ratings`
- DB: `share_comments`, `block_ratings` tables, `allow_feedback`/`allow_ratings` on `project_shares` (migration 015)

### 21. Project Templates
- ~25 seed templates across all 16 concept categories (Coffee Shop, iOS App, Short Film, Online Course, SaaS Platform, Podcast, E-commerce, etc.)
- Displayed in a category-grouped TemplateGrid on the Home page
- Selecting a template pre-populates design sheet fields at ~40% confidence
- Seed data: `project_templates.seed.json`
- Endpoint: `GET /templates`

### 22. Voice Discovery
- Browser Web Speech API — zero backend cost
- `useVoiceInput` hook: `isListening`, `transcript`, `isSupported`, `startListening`, `stopListening`, `resetTranscript`
- VoiceMicButton component with pulsing animation, hidden when browser doesn't support
- Real-time transcript populates the Discovery chat input

### 23. Concept Branching
- Git-like project forking for exploring alternative directions
- Deep-copies project and all child records into a new branch
- Compare two branches side-by-side
- Merge branch back into parent
- Branch indicators visible in Library page
- Endpoints: `POST /projects/{id}/branch`, `POST /projects/{id}/merge/{branch_id}`, `GET /projects/{id}/branches`, `GET /projects/{id}/compare/{branch_id}`
- DB: `concept_branches` table (migration 016)

### 24. External Integrations (de-scoped — coming soon)
- 6 planned integrations: Notion, Trello, Linear, Figma, Google Docs, Airtable
- Currently de-scoped: unconnected providers return `status: "coming_soon"`
- OAuth connect/disconnect per provider (infrastructure in place)
- Push project data to connected tools (design kit → formatted output per platform)
- Encrypted token storage (Fernet) for stored OAuth credentials
- Endpoints: `GET /integrations`, `GET /integrations/{provider}/auth`, `POST /integrations/{provider}/callback`, `DELETE /integrations/{provider}`, `POST /integrations/{provider}/push/{project_id}`
- DB: `user_integrations` table (migration 016)

### 25. Admin Dashboard
- Hidden `/admin` route gated by `users.is_admin`; non-admins see a polite access-denied panel
- Sidebar shows "Admin" link with 🛡 shield icon only when `user.is_admin === true`
- Two tabs: **Users** (paginated, searchable user table) and **Audit Log**
- User drawer (opens on row click): identity + Stripe/Clerk IDs, plan selector (free/basic/pro), usage counts, entitlement overrides editor (Inherit / Unlimited / Custom per limit key), grant/revoke admin toggle
- **Entitlement overrides** live in `users.entitlement_overrides` (JSONB); `entitlement_service.get_limits()` merges them over plan defaults — any key present in overrides wins, `null` means unlimited for that key
- **Audit log** (`admin_audit_log` table) is append-only — records `admin_user_id`, `action`, `target_user_id`, `details` (before/after JSON), `created_at`
- Audit-logged actions: `plan_changed`, `plan_unchanged`, `overrides_updated`, `admin_granted`, `admin_revoked`
- Self-revoke of admin status blocked at the API layer to prevent lockout
- Backend: `app/routers/admin.py` (with `require_admin` dep), `app/services/audit_service.py`, `app/schemas/admin.py`
- Frontend: `pages/Admin.tsx`, `components/admin/AdminUserTable.tsx`, `components/admin/AdminUserDrawer.tsx`, `components/admin/AdminAuditList.tsx`, `stores/adminStore.ts`
- Endpoints: `GET /admin/users`, `GET /admin/users/{id}`, `PATCH /admin/users/{id}/plan`, `PATCH /admin/users/{id}/overrides`, `PATCH /admin/users/{id}/admin`, `GET /admin/audit-log`
- **First admin bootstrap:** `UPDATE users SET is_admin = TRUE WHERE id = '<id from /auth/me>';` — always use the `id` returned by `/auth/me` (orphan duplicate user rows from old Clerk webhook races can exist; the `/auth/me` id is the canonical row)
- DB: migrations 027 (`is_admin` + `entitlement_overrides`), 028 (`admin_audit_log`)

---

## Design System

- **Theme:** Dark glassmorphism — `#0d0d12` background, `bg-white/5` cards, `backdrop-blur`, `border: 1px solid rgba(255,255,255,0.08)`
- **Accent:** Electric cyan `#00E5FF` — `text-accent`, `border-accent`, `bg-accent/10`
- **Selected state:** `bg-accent/5 border-accent shadow-[0_0_16px_rgba(0,229,255,0.1)]`
- **Typography:** Arial (Regular for body, Bold for emphasis, Black for headings), JetBrains Mono (code/prompts)
- **Cards:** 12px radius, glass border, hover `border-white/15` + `scale-[1.02]`
- **Animations:** Framer Motion — page transitions, IdeaNebulaCanvas, skeleton loaders
- **State:** Zustand stores + React Query for server state
- **Tailwind v4:** CSS-based config, no `tailwind.config.js`
- **Notifications:** react-hot-toast
- **Responsive:** sidebar collapses to bottom nav on <768px

---

## Database Migrations (linear chain)

| # | Description |
|---|-------------|
| 001 | Initial schema (users, projects, sessions, design_sheets, blocks) |
| 002 | Market analyses table |
| 003 | Project snapshots |
| 004 | OAuth + profile fields |
| 005 | User memory |
| 006 | Project shares |
| 007 | Sprint plans |
| 008 | Sprint error message patch |
| 009 | Pathway infrastructure (pathway_id on projects, stages on sessions) |
| 010 | AI partner style (ai_partner_style on projects + sessions) |
| 011 | Modular pathway system (categories on projects, module_pathways, module_responses) |
| 012 | Email verification (email_verified on users, email_verifications table) |
| 013 | User profile fields (account_type, bio on users) |
| 014 | Idea inbox (idea_inbox_items table, inbox_email on users) |
| 015 | Sharing feedback + templates (allow_feedback/allow_ratings on project_shares, share_comments, block_ratings) |
| 016 | Concept branches + external integrations (concept_branches, user_integrations tables) |
| 017 | Seed project templates |
| 018 | Seed category templates |
| 019 | Add stripe_customer_id to users |
| 020 | Add password_resets table (legacy — now handled by Clerk) |
| 021 | Add clerk_user_id to users |
| 022 | Widen avatar_url column to TEXT |
| 023 | Deduplicate user rows (webhook cleanup) |
| 024 | Expand templates to 160 |
| 025 | Inbound email idempotency (provider_event_id unique constraint) |
| 026 | Deduplicate user rows v2 (post-Clerk webhook race cleanup) |
| 027 | Add `users.is_admin` (bool) + `users.entitlement_overrides` (JSONB) |
| 028 | Create `admin_audit_log` table (append-only admin action log) |
| 029 | Add `projects.flow_version` (legacy `v1` vs unified `v2` flow) |
| 030 | Phase-2 hotfix — backfill `module_pathways.modules` shape, dedup `module_responses`, add UNIQUE(project_id, module_id) |
| 031 | Add `sessions.scope_module_ids` (JSONB, nullable) for mini-Discovery scoped sessions |
| 032 | Add Stripe subscription state columns (`stripe_subscription_id`, `subscription_status`, `subscription_price_id`, `subscription_current_period_end`) to users |

---

## API Routes (prefix: `/api/v1`)

| Domain | Key Routes |
|--------|------------|
| Auth | `GET /auth/me`, `PATCH /auth/me`, `POST /auth/me/avatar`, `GET /auth/me/entitlements` (Clerk handles sign-in/sign-up) |
| Billing | `POST /billing/checkout`, `POST /billing/portal`, `POST /billing/webhook` |
| Clerk Webhook | `POST /webhooks/clerk` (user sync) |
| Projects | `POST /projects`, `GET /projects/{id}`, `PATCH /projects/{id}` |
| Pathways | `GET /pathways`, `POST /pathways/detect` |
| Meta | `GET /meta/partner-styles` |
| Discovery | `POST /discovery/start` (body: project_id), `POST /discovery/{session_id}/init` (SSE), `POST /discovery/{session_id}/message` (SSE), `PATCH /discovery/{session_id}/partner`, `PATCH /discovery/{session_id}/progress`, `GET /discovery/{session_id}`, `GET /discovery/{session_id}/sheet`, `GET /discovery/{session_id}/field-summary` (v2 only — returns 409 for v1), `GET /discovery/{session_id}/transcript?format=md\|pdf\|txt` |
| Blocks | `GET /projects/{project_id}/blocks`, `POST /projects/{project_id}/blocks`, `POST /projects/{project_id}/blocks/generate`, `PATCH /projects/{project_id}/blocks/{block_id}`, `DELETE /projects/{project_id}/blocks/{block_id}` |
| Pipeline | `GET /projects/{id}/pipeline`, `POST /projects/{id}/pipeline/recommend`, `PATCH /projects/{id}/pipeline/{layer}`, `POST /projects/{id}/pipeline/ui-skeleton` |
| Exports | `GET /projects/{id}/export?format=md\|pdf\|docx\|zip` |
| Market | `POST /market/{project_id}/generate` (SSE), `GET /market/{project_id}`, `GET /market/{project_id}/report`, `GET /market/{project_id}/export` |
| Sprints | `POST /sprints/{project_id}/generate` |
| Sharing | Project share CRUD, `POST/GET /sharing/public/{token}/comments`, `POST/GET /sharing/public/{token}/ratings` |
| Library | `GET /library/projects`, `POST /library/{project_id}/snapshots`, `GET /library/{project_id}/snapshots`, `POST /library/snapshots/{snapshot_id}/restore`, `POST /library/{project_id}/export`, `POST /library/import` |
| Module Pathway | `POST /projects/{project_id}/categorize`, `POST /projects/{project_id}/pathway/assemble`, `GET /projects/{project_id}/pathway`, `PATCH /projects/{project_id}/pathway`, `POST /projects/{project_id}/pathway/lock`, `GET /projects/{project_id}/design-kit`, `POST /projects/{project_id}/pathway/modules` |
| Modules | `POST /modules/{id}/{module_id}/start` (SSE), `POST /modules/{id}/{module_id}/respond` (SSE), `POST /modules/{id}/{module_id}/skip`, `GET /modules/{id}/{module_id}/summary`, `PATCH /modules/{id}/{module_id}/responses`, `POST /modules/{id}/{module_id}/refresh-output` |
| Inbox | `GET /inbox`, `POST /inbox`, `GET /inbox/count`, `GET /inbox/stream` (SSE), `POST /inbox/{id}/promote`, `DELETE /inbox/{id}` |
| Templates | `GET /templates` |
| Branching | `POST /branching/{project_id}/branch`, `POST /branching/{project_id}/merge/{branch_id}`, `GET /branching/{project_id}/branches`, `GET /branching/{project_id}/compare/{branch_id}` |
| Integrations | `GET /integrations`, `GET /integrations/{provider}/auth`, `POST /integrations/{provider}/callback`, `DELETE /integrations/{provider}`, `POST /integrations/{provider}/push/{project_id}` |
| Webhooks | `POST /webhooks/inbound-email` |
| Admin | `GET /admin/users`, `GET /admin/users/{id}`, `PATCH /admin/users/{id}/plan`, `PATCH /admin/users/{id}/overrides`, `PATCH /admin/users/{id}/admin`, `GET /admin/audit-log` |

---

## Critical Rules

1. **Each AI Partner must genuinely live up to its namesake in behavior. Not cosmetic.** Every partner fragment contains detailed behavioral instructions with Core Behaviour, Questioning Style, and Guardrails.
2. **Structured output schema is never altered by partner choice.** Partners change *how* the AI collaborates, not *what* gets extracted.
3. **All API routes are prefixed with `/api/v1`.**
4. **All DB models use UUIDs as primary keys.**
5. **Frontend: hooks only, no class components. Zustand for local state, React Query for server state.**
6. **Railway deployment: both services auto-deploy on push to `main`. No reverse proxy — backend and frontend are exposed publicly.**
7. **Partner style default is `"strategist"` everywhere (model defaults, schema defaults, frontend state init).**
8. **No preview verification required.** Do not start dev servers or take screenshots to verify code changes. The user handles testing manually.
9. **Before declaring a code-touching task complete, run the [Documentation Discipline](#documentation-discipline) checklist.** Bump affected versioned docs and add a CHANGELOG.md entry. The Stop hook will nag if you skip CHANGELOG.

---

## Known Issues

1. **Node.js v24 + Vite 7 ESM:** Local preview tool can't run Vite dev server due to ESM/require() incompatibility. Builds verified via `tsc -b` and `vite build`.
2. **C: drive space:** Vite builds may fail if C: is full. Use `TMPDIR=D:/tmp` when building locally.
3. **Integration tests:** 4 tests in `backend/tests/test_partner_style.py` require the `anthropic` module (only on Railway). The 24 unit tests run locally with just pytest.
4. **PartnerSelector component** is used in `Discovery.tsx` for mid-session switching. It was removed from `Home.tsx` in favor of the inline grid.

---

## Git Workflow

- When asked to push changes, ALWAYS verify with `git status` and `git log` before claiming completion.
- Never say changes are pushed without confirming via actual shell output.
- Commit messages follow conventional commits format.

---

## Session Recovery

**Read in this order on every session start:**
1. **`CLAUDE.md`** (this file) — project identity, features, critical rules
2. **`DOC_VERSIONING.md`** — doc-versioning convention (read once, refer back when committing doc-touching work)
3. **`MEMORY.md`** — conventions, common pitfalls, architecture mental model
4. **`CONTEXT_HANDOFF.md`** — latest session state, what just shipped, what's open
5. **`TODO.md`** — concrete next steps prioritized by blocker → high → nice-to-have
6. **`CHANGELOG.md`** — what changed recently (skim the most recent dated entry to see the project's current arc)
7. **`ROADMAP.md`** — only when discussing forward direction

**Working directory:** ALWAYS `C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\`. Older docs may reference `D:\Development\Ide_AI\` or `D:\Development\ideaFORGE\` — those paths are obsolete.

**Platform:** Windows. Use `npm.cmd` not `npm`, `python` not `python3`. Type-check after every frontend change: `npx.cmd tsc -b --noEmit`. Validate Python syntax via `python -c "import ast; ast.parse(open('...').read())"`.

---

## Documentation

This project follows the [DOC_VERSIONING.md](DOC_VERSIONING.md) convention — SemVer per doc, root [CHANGELOG.md](CHANGELOG.md), manual discipline. When you ship code that changes a documented feature, bump the affected doc's version + last-updated date and add a CHANGELOG entry. See `DOC_VERSIONING.md` for the full checklist.

---

## Last Completed Task

**Task:** Documentation reconciliation + CI workflow + asset commit.

Follow-up to the 12-task Codex alignment audit. Committed `.github/workflows/test-pipeline.yml` (CI) and `frontend/public/og-image.psd` (OG image source). Full documentation audit: verified every claim in CLAUDE.md against disk (models, types, module count, test counts), fixed 3 discrepancies (missing `admin_audit_log.py` model, incomplete types listing, stale "47 modules" → 40).

**Date:** 2026-05-28
**Test coverage:** 229/229 backend tests pass (9 files). 37/37 frontend tests pass (5 files). TypeScript build clean.
**Pending:** Rotate 3 webhook secrets (CLERK, STRIPE, RESEND). Create `frontend/public/og-image.png` from PSD (1200×630). Add rate limiting on sharing endpoints (SAST-H1). js-cookie CVE is upstream from `@clerk/shared` (DEP-H1).
