# Ide/AI — Context Handoff Document

> Single source of truth for the current state of the project.
> Use this when starting a new Claude Code session.
> **Last updated:** 2026-05-23

---

## What is Ide/AI?

Ide/AI takes a rough idea and turns it into a structured, export-ready design kit before the user opens a builder tool. The core problem: people waste credits, time, and money figuring out what to build inside metered platforms (Bubble, Cursor, Claude Code, Bolt, etc.) when that planning should happen beforehand.

The full process: describe an idea → configure options → AI-guided discovery conversation → modular pathway → walk away with a prioritized feature breakdown, tech stack recommendation, platform-specific prompts, and exportable docs.

**Live deployment:** Railway (backend + frontend as separate public services)
**Frontend URL:** https://myide.ai
**Backend URL:** https://backend-production-9c212.up.railway.app
**Working directory:** `C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\` (NOT `D:\`)

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL, Anthropic Claude API (claude-sonnet-4-6) |
| **Frontend** | React 19.2, TypeScript, Vite 7.3, Tailwind CSS v4 (CSS-based config, no `tailwind.config.js`), Framer Motion, Zustand |
| **Auth** | Clerk (Google/Microsoft/GitHub OAuth + email/password) |
| **Billing** | Stripe (checkout sessions, billing portal, webhook sync) |
| **Email** | Resend API — inbound email webhooks for Idea Inbox |
| **Toasts** | react-hot-toast (global Toaster in App.tsx) |
| **Drag-and-drop** | @dnd-kit/core + sortable + utilities (Blocks board) |
| **Flow diagram** | reactflow (PitchMode user flow) |
| **Deployment** | Railway (2 services), Docker, Caddy (frontend static) |
| **AI Streaming** | Server-Sent Events (SSE) for discovery chat, market analysis, module responses |
| **Export** | fpdf2 (PDF), python-docx (DOCX), Jinja2 templates, ZIP bundling |

---

## Current Session (2026-05-23) — Audit Completion + Mobile Fixes

This session completed the comprehensive audit from the previous "Last Completed Task" period AND fixed two user-reported mobile/UX bugs. Every code change was verified by 2 parallel agents (edge-case + integration) before being marked complete.

### Commits this session (5 total, all pushed to main)

| Hash | Commit | Files |
|------|--------|-------|
| `9c5ef1c` | fix: transcript copy includes AI messages + add Save Place button | 2 |
| `5db42eb` | feat: close 5 critical spec gaps from audit | 6 |
| `253b30a` | feat: close all 8 remaining audit findings with 2-agent verification per fix | 16 |
| `fb1f1b8` | fix: mobile viewport conformance + surface PathwayReview errors | 24 |

### Tasks completed (15 total)

#### Critical user reports
- **Transcript copy fix** — Was only copying user messages. Backend was fine; frontend Axios needed `responseType: 'text'` so the `text/markdown` response wasn't mishandled. Fallback also normalized to include both roles.
- **Save Place button** — New 🔖 button in Discovery TopBar. Calls existing `PATCH /discovery/{id}/progress` endpoint. Cycles idle → "Saving…" → "Place Saved!" states.
- **Discovery mobile viewport** — `h-screen` (100vh) ignored iOS URL bar pushing content off-screen; `pb-14` ignored iPhone home indicator. Fixed across 19 pages with new `.h-dvh` and `.pb-mobile-nav` utilities + horizontally scrollable TopBar actions row.
- **Proceed button errors** — User got stuck on infinite spinner when categorize/assemble failed. `fetchPathway` polluted error state on expected 404; `init()` console.error'd silent failures. Now surfaces all errors via toast + inline banner, advances to review step on failure for retry.

#### 5 critical spec gaps (from audit)
1. **Home pathway hardcoding** — Was always `software_product`. Now calls `POST /pathways/detect` with the user's idea description and uses returned `pathway_id`.
2. **VoiceMicButton wired** — Component existed but never imported. Now in Discovery textarea row, Web Speech API populates input live.
3. **Drag-and-drop Blocks** — Installed `@dnd-kit/core` + `sortable` + `utilities`. Keyboard-accessible drag handle, optimistic UI, parallel PATCH for changed `sort_order`.
4. **Inbox endpoint docs aligned** — Frontend & backend both use `/inbox/{id}/promote`; CLAUDE.md said `/build`. Corrected.
5. **Home config selectors** — Added collapsible Advanced panel with platform/audience/complexity/tone dropdowns.

#### 8 remaining audit findings
6. **SSE event reorder** — `sheet_update` now fires BEFORE `done` so clients that close on the done sentinel still receive updates. `sheet_data` dict built before `db.commit()` for async safety.
7. **CLAUDE.md drift** — Working dir corrected (D:\ → C:\Users\vybec\…), Discovery API row matched code, Blocks/Library/ModulePathway/Branching rows corrected, migrations 024–026 added.
8. **react-hot-toast** — Installed + global Toaster in App.tsx with glassmorphism styling. Inbox page converted from inline error banner to `toast.error`/`toast.success`.
9. **Sidebar inbox unread badge** — New `inboxStore` (Zustand) with `refresh()` + `adjust(delta)` actions. 60s polling gated on `isSignedIn`. Inbox page calls `adjust()` after add/delete/promote for instant feedback. Badge on all 3 nav surfaces.
10. **Inbox per-item AI partner picker** — Backend `InboxPromote` schema accepts optional `ai_partner_style`, validates with fallback. Frontend renders `<select>` per item.
11. **UpgradeModal naming collision** — `ui/UpgradeModal.tsx` (limit notice) renamed to `ui/EntitlementLimitModal.tsx`. `billing/UpgradeModal.tsx` (plan picker with checkout) kept as canonical. All 5 page imports updated.
12. **PitchMode React Flow diagram** — Installed `reactflow`, added linear Start → F0 → … → Done diagram from up to 6 MVP blocks. Read-only, keyboard-accessible. Print CSS overrides for legibility.
13. **auth.py race refactor** — Extracted `_link_existing_email_user` and `_idempotent_create_user` helpers. Uses PostgreSQL `INSERT ... ON CONFLICT (clerk_user_id) DO NOTHING` to collapse the webhook race window. Reduced 5 inline branches to 3 clearer steps.

---

## What's Working Today (verified)

- **Auth pipeline** — Clerk JWKS verification, INSERT ON CONFLICT race handling, webhook svix HMAC, migration 026 dedup
- **Discovery SSE** — `done` event always fires (try/except wrapped), safety-net `onDone` in `useSSE`, anti-repetition CONVERSATION RULES injected, `sheet_update` fires BEFORE `done`
- **Backend ownership/entitlement gates** — Every project/session route filters by `user_id`; every creation path gated by plan limit (free=3 projects / basic=25 / pro=unlimited)
- **Migration chain** — Linear 001→026, all `down_revision` correct, all child-table names match models
- **Mobile viewport** — All 19 affected pages use `.h-dvh` + `.pb-mobile-nav`, Sidebar nav extends for safe-area, TopBar actions horizontally scrollable
- **Error surfacing** — react-hot-toast globally available, PathwayReview shows toast + banner on failure
- **CLAUDE.md** — Endpoint table matches actual code, working-dir path corrected, all migrations 001–026 listed
- **Partner styles** — 10 styles substantive (Behaviour/Questioning/Guardrails), default `strategist` consistent everywhere

---

## What Still Needs Your Action

### 🚦 Railway deployment config (4 items — required for production)

These cannot be set from code; they need to be added in the Railway backend service's env vars panel:

1. **`CORS_ORIGINS`** = `["https://myide.ai","https://www.myide.ai"]`
   - Default is only `localhost:5173`. Without this, ALL authenticated requests fail in production.

2. **Clerk hardening (3 vars)** — currently optional but should be set:
   - `CLERK_ISSUER` = `https://<your-instance>.clerk.accounts.dev`
   - `CLERK_AUDIENCE` = `<your-app-audience>` (if you use audience claims)
   - `CLERK_AUTHORIZED_PARTIES` = `https://myide.ai` (comma-separated)
   - Without these, any RS256 token from any Clerk instance validates.

3. **`INTEGRATION_TOKEN_KEY`** — generate via:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   - Only needed if you re-enable integrations (currently `status: "coming_soon"`). Low launch impact.

4. **Verify already set:** `RESEND_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`. Both required for inbound email + Stripe webhook signature verification.

### 🧹 Code follow-ups (low priority — not blocking)

- **`ModuleSession.tsx:73` and `PathwayExecute.tsx:43`** call `fetchPathway(projectId)` without try/catch. Since `fetchPathway` now re-throws on all errors (including 404), an unhandled rejection could surface in dev tools. Wrap in try/catch.
- **Other pages still use `setError` patterns** — Profile, SharedProject, SprintPlanner, Home (createError), CommentSection, StarRating, billing/UpgradeModal. Could migrate to `toast.error` for consistency. ~9 sites.
- **Silent `console.error` failures** — Discovery (8 sites), Blocks (5 sites), Library, Pipeline, Exports, PromptKit, PitchMode, ModuleSession, MarketAnalysis, PathwayReview, ShareDialog, TemplateGrid, TranscriptExportMenu, pathwayStore. These log but don't notify the user. Should add `toast.error()` calls.
- **Duplicate `_partnerCache`** in Home.tsx and Inbox.tsx — could be hoisted to `lib/partnerCache.ts`. Currently independent fetches.
- **Cross-tab inbox badge sync** — Sidebar polls every 60s but doesn't listen to `storage` events. Adding ideas in tab A shows in tab B after up to 60s.

---

## Recent History (older work, still relevant)

### Session 2 — Post-Update Audit (2026-05-21)
- Discovery autosave rewrite (ref-based, no message-array overwrite)
- Empty-session recovery (jsonb_array_length to prefer non-empty)
- Library resume routing (stage gate before routing past Discovery)
- Pathway completion sync after module complete/skip
- Svix webhook verification + Resend idempotency (migration 025)
- Private share viewer JWT tokens (6hr, HS256)
- Centralized entitlement guards on all creation paths
- Frontend lint cleanup (0 errors)
- Backend test infrastructure (37 tests passing)

### Session 1 — Codebase Audit (earlier)
- Discovery session resume idempotency
- Inbox promotion `owner_id` → `user_id` fix
- Branch creation fix + parent metadata copy
- ShareDialog route fixes
- Module session resume support

### Earlier (2026-05-22)
- Duplicate user crash fix (auth.py race handling + migration 026 dedup)
- Quick chips always appear (event_stream try/except wrapping)
- Design sheet update fix (`extract_sheet_fields` JSON parsing robustness)
- AI partner anti-repetition (CONVERSATION RULES block with message_count)

---

## Database Migrations (linear chain: 001-026)

| # | Description |
|---|-------------|
| 001-010 | Original schema through AI partner styles |
| 011 | Modular pathway system |
| 012 | Email verification (legacy) |
| 013 | User profile fields (account_type, bio) |
| 014 | Idea inbox |
| 015 | Sharing feedback + templates |
| 016 | Concept branches + external integrations |
| 017 | Seed project templates |
| 018 | Seed category templates |
| 019 | Add stripe_customer_id to users |
| 020 | Add password_resets table (legacy) |
| 021 | Add clerk_user_id to users |
| 022 | Widen avatar_url to TEXT |
| 023 | Deduplicate user rows (webhook cleanup v1) |
| 024 | Replace all system templates with 160 across 16 categories |
| 025 | Add provider_event_id to idea_inbox (Svix idempotency) |
| 026 | Deduplicate user rows v2 (post-Clerk webhook race cleanup) |

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
- `INBOX_DOMAIN` — Domain for generated inbox emails (e.g. `inbox.myide.ai`)
- 4× `STRIPE_PRICE_*` — Basic/Pro Monthly/Yearly price IDs

### Backend (optional but recommended for production)
- `CORS_ORIGINS` — JSON list of allowed origins (default: `["localhost:5173"]`)
- `CLERK_ISSUER` — Expected JWT issuer
- `CLERK_AUDIENCE` — Expected JWT audience
- `CLERK_AUTHORIZED_PARTIES` — Comma-separated allowed azp values
- `RESEND_API_KEY` — Resend API key for outbound email
- `RESEND_WEBHOOK_SECRET` — Svix signing secret for inbound email
- `INTEGRATION_TOKEN_KEY` — Fernet key for encrypting integration OAuth tokens
- `SHARE_ACCESS_SECRET` — JWT secret for viewer tokens (falls back to CLERK_SECRET_KEY)

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

**Frontend has no test files** — verification is via `npx tsc -b --noEmit` only.

---

## Key Files for New Sessions

| Purpose | File |
|---------|------|
| Project instructions | `CLAUDE.md` |
| This handoff | `CONTEXT_HANDOFF.md` |
| Forward roadmap | `ROADMAP.md` |
| Concrete todos | `TODO.md` |
| AI partner spec | `AI_PARTNER_SELECTOR_SPEC.md` |
| Architecture diagrams | `ARCHITECTURE.md` |
| Seed data (categories) | `backend/app/data/concept_categories.seed.json` |
| Seed data (modules) | `backend/app/data/module_library.seed.json` |
| Seed data (templates) | `project_templates.seed.json` |
| Audit package | `docs/claude-code-package/2026-05-21-post-update-audit/` |
| Clerk auth | `backend/app/core/clerk.py`, `backend/app/routers/auth.py` |
| Stripe billing | `backend/app/routers/billing.py` |
| Entitlements | `backend/app/services/entitlement_service.py` |
| Inbox badge store | `frontend/src/stores/inboxStore.ts` |
| Entitlement limit modal | `frontend/src/components/ui/EntitlementLimitModal.tsx` |
| Plan picker modal | `frontend/src/components/billing/UpgradeModal.tsx` |
| Error helpers | `frontend/src/lib/extractError.ts` |
| Voice input | `frontend/src/hooks/useVoiceInput.ts`, `components/voice/VoiceMicButton.tsx` |
| Test fixtures | `backend/tests/conftest.py` |
| Shared categories | `frontend/src/lib/categories.ts` |
| Global Toaster + Routes | `frontend/src/App.tsx` |
| Mobile-aware layout | `frontend/src/styles/globals.css` (.h-dvh, .pb-mobile-nav) |

---

## Code Quality Snapshot (2026-05-23)

- ✅ TypeScript: zero compilation errors
- ✅ Backend Python: syntax validated on all changed files
- ✅ Migration chain: linear 001→026, all alembic IDs match
- ✅ Auth: 5 race branches consolidated to 3 with INSERT ON CONFLICT
- ✅ SSE: always emits `done`, sheet_update fires before done
- ✅ Mobile: 19 pages use dynamic viewport + safe-area utilities
- ✅ Error UX: react-hot-toast wired, PathwayReview surfaces errors
- ⚠️ Railway env vars: 4 items need user action before launch
- ⚠️ Other pages: ~17 sites still use `setError` or silent `console.error` (cosmetic)
- ⚠️ 2 callers of `fetchPathway` lack try/catch (ModuleSession, PathwayExecute)
- ❌ Frontend tests: none exist (TypeScript build is the only verification)
