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

Two audit sessions completed. The first covered P0 bugs, security hardening, and product completion. The second implemented the post-update audit package.

### Session 2 — Post-Update Audit (latest)

#### P0 Fixes
- **Discovery autosave rewrite** — Eliminated message-array overwrite; ref-based saves on interval/visibility/unmount/stage-change. Backend progress endpoint validates stale clients via `client_message_count`.
- **Empty-session recovery** — `get_latest_active_session_for_project` now uses `jsonb_array_length` to prefer non-empty sessions and retires empty orphans as "abandoned".
- **Library resume routing** — `_compute_resume_path` checks `discovery_stage in {"confirm", "complete"}` before routing past Discovery.
- **Pathway completion sync** — `_sync_pathway_completion()` runs after module complete/skip, updates `ModulePathway.status` when all modules done.

#### P1 Security & Quality
- **Svix webhook verification** — Resend inbound email webhook uses `svix.webhooks.Webhook.verify()` with idempotency via `provider_event_id` column (migration 025).
- **Private share viewer tokens** — JWT-based access tokens (6hr, HS256) for password-protected share feedback endpoints. All 6 feedback routes require Bearer token for private shares.
- **Frontend share token passthrough** — `shareAccessToken` threaded from SharedProject through FeedbackPanel, CommentSection, StarRating.
- **Centralized entitlement guards** — `require_project_slot()` and `require_feature_usage()` wired into all project-creation paths (projects, templates, inbox, branching, .ideai import) and feature routes (market, prompts, sprints).
- **Integration token encryption** — Both `encrypt_secret()` calls wrapped in try/except RuntimeError -> 503.
- **Frontend lint: zero errors** — Fixed 18 lint issues across 10 files: setState-in-effect (lazy initializers, render-time state sync), refs-during-render (state-based previous-value pattern), Fast Refresh (extracted categories to `lib/categories.ts`), exhaustive-deps, immutability.
- **Backend test infrastructure** — `conftest.py` with async in-memory SQLite, JSONB/UUID compat shims, `jsonb_array_length` UDF. 37 tests passing (24 partner style + 4 discovery resume + 9 entitlements).

#### P2 Docs
- **`.env.example` updated** — All env vars documented (Clerk, Stripe, Resend, SHARE_ACCESS_SECRET, INTEGRATION_TOKEN_KEY).

### Session 1 — Codebase Audit (earlier)

#### P0 Fixes
- **Discovery session resume** — `POST /discovery/start` is idempotent; returns existing active session.
- **Inbox promotion crash** — Fixed `owner_id` -> `user_id`.
- **Branch creation crash** — Fixed `owner_id` -> `user_id` + parent metadata copy.
- **ShareDialog routes** — Fixed 3 mismatched frontend routes.
- **Module session resume** — Active sessions return existing messages; complete sessions show transcript.

#### Security Hardening
- Sharing/sprint ownership checks, expiry enforcement, JWT hardening, HMAC webhook, token encryption, payload limits.

#### Product Completion
- Library progress metadata + smart resume, snapshot unification, sharing feedback UI, branching deep copy, PromptKit page, entitlement service, dependency upgrades, rebrand.

---

## Database Migrations (linear chain: 001-025)

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
| 024 | Replace all system templates with 160 templates across 16 categories |
| 025 | Add provider_event_id to idea_inbox_items (Svix idempotency) |

---

## Environment Variables

### Backend (required)
- `DATABASE_URL` — PostgreSQL connection string
- `ANTHROPIC_KEY` — Claude API key
- `CLERK_SECRET_KEY` — Clerk backend secret
- `CLERK_WEBHOOK_SECRET` — Clerk webhook signing secret
- `STRIPE_SECRET_KEY` — Stripe backend secret
- `STRIPE_WEBHOOK_SECRET` — Stripe webhook signing secret
- `FRONTEND_URL` — Frontend origin for CORS/share links

### Backend (optional, security hardening)
- `CLERK_ISSUER` — Expected JWT issuer
- `CLERK_AUDIENCE` — Expected JWT audience
- `CLERK_AUTHORIZED_PARTIES` — Comma-separated allowed azp values
- `RESEND_WEBHOOK_SECRET` — Svix signing secret for Resend inbound email
- `INTEGRATION_TOKEN_KEY` — Fernet key for encrypting integration tokens
- `SHARE_ACCESS_SECRET` — JWT secret for viewer access tokens (falls back to CLERK_SECRET_KEY)

### Frontend
- `VITE_CLERK_PUBLISHABLE_KEY` — Clerk frontend key
- `VITE_API_BASE_URL` — Backend API base URL (defaults to `/api/v1`)
- `VITE_STRIPE_PUBLISHABLE_KEY` — Stripe frontend key

---

## Test Suite

Run from `backend/`:

```bash
# All tests (excluding anthropic-dependent integration tests):
python -m pytest tests/ -v -k "not PromptComposition"

# Quick partner style tests (no DB needed):
python -m pytest tests/test_partner_style.py -v -k "not PromptComposition"

# Discovery resume tests (requires async DB fixtures):
python -m pytest tests/test_discovery_resume.py -v

# Entitlement tests:
python -m pytest tests/test_entitlements.py -v
```

Required pip packages: `pytest pytest-asyncio aiosqlite sqlalchemy[asyncio] pydantic-settings python-dotenv fastapi anthropic`

---

## Session 3 — P2 Completion (latest)

#### P2: Branching Completeness
- **`_gather_project_state`** now serializes `fields_data` (DesignSheet) and `ai_partner_style` (DiscoverySession).
- **`_copy_child_records`** now restores all previously-missing fields:
  - `fields_data` on DesignSheet (pathway-specific custom fields)
  - `ai_partner_style` on DiscoverySession (preserves partner choice)
  - `completed_at` on ModuleResponse (with safe ISO datetime parsing)
  - Entire `MarketAnalysis` model (was completely missing — caused data loss on branch + merge)
- **MarketAnalysis import** moved from inline in `merge_branch` to top-level.

#### P2: Product UX — Entitlement Upgrade Modals
- **`UpgradeModal`** component (`frontend/src/components/ui/UpgradeModal.tsx`) — glassmorphism modal showing plan name, usage bar, current/limit counts, and "View Plans" CTA.
- **`extractError.ts`** — Added `EntitlementDetail` type, `getEntitlementDetail()`, and `isEntitlementError()` helpers. `extractError()` now returns the human-readable message for entitlement 403s.
- **Wired into 5 pages:** Home (project creation), PromptKit (generate), MarketAnalysis (generate SSE), SprintPlanner (generate SSE), Inbox (promote to project). All catch blocks detect 403 entitlement errors and show the modal instead of silent failures.
- Raw `fetch` SSE endpoints (MarketAnalysis, SprintPlanner) parse the 403 JSON body before throwing.

#### P2: Docs Cleanup
- **`README.md`** — Fixed `ANTHROPIC_API_KEY` → `ANTHROPIC_KEY` naming inconsistency.
- **`frontend/README.md`** — Replaced Vite boilerplate with Ide/AI-specific guide (stack, env vars, scripts, project structure, design system).

---

#### Misc
- **`datetime.utcnow()` deprecation** — Replaced all 7 instances across `discovery_service.py`, `market_export_service.py`, and `transcript_service.py` with `datetime.now(timezone.utc)`. Zero deprecation warnings in tests.

#### P2: Branching Merge Conflict Resolution
- **Pre-merge auto-snapshot** — Merge endpoint now creates a `ProjectSnapshot` before overwriting, with auto-incremented version. Snapshot name includes branch name and sections.
- **Selective merge** — New optional `MergeRequest` body with `sections` list (e.g. `["blocks", "pipeline"]`). Only listed sections are deleted + replaced; un-listed sections stay untouched. Omit for full overwrite (backwards compatible).
- **Diff annotations on compare** — `GET /compare/{branch_id}` now returns a `diff` dict with per-section `changed`, `parent_summary`, and `branch_summary` so the frontend can show which sections diverge.
- **Section-aware `_copy_child_records`** — Refactored with `include` filter; each section wrapped in an `if "key" in include` guard. `_SECTION_MODELS` maps section keys to ORM models for selective deletion.
- **Invalid section validation** — Merge endpoint returns 422 with valid section list if unknown sections are passed.

#### P2: Architecture Diagrams
- **ARCHITECTURE.md** updated with 6 Mermaid diagrams: system architecture, request lifecycle, discovery state machine, modular pathway flow, branching/merge, entitlement gate flow.
- **Database schema** section corrected (fields_data, completed_at, market_analysis columns, etc.).

#### P2: API Docs
- FastAPI already auto-generates docs at `/api/docs` (Swagger UI) and `/api/redoc` (ReDoc). Documented in ARCHITECTURE.md.

---

## Remaining Work

All audit items complete. No remaining P0/P1/P2 items from either audit session.

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
| Audit package | `docs/claude-code-package/2026-05-21-post-update-audit/` |
| Clerk auth | `backend/app/core/clerk.py` |
| Stripe billing | `backend/app/routers/billing.py` |
| Entitlements | `backend/app/services/entitlement_service.py` |
| Upgrade modal | `frontend/src/components/ui/UpgradeModal.tsx` |
| Error helpers | `frontend/src/lib/extractError.ts` |
| Test fixtures | `backend/tests/conftest.py` |
| Shared categories | `frontend/src/lib/categories.ts` |
