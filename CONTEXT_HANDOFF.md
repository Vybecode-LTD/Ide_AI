# Ide/AI — Context Handoff Document

> **Version:** 2.0.0 · **Last updated:** 2026-05-23 · See [CHANGELOG.md](CHANGELOG.md)
>
> Single source of truth for the current state of the project.
> Use this when starting a new Claude Code session.

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

## Current Session (2026-05-23) — Admin System + Error UX + Doc Versioning

Three logical chunks: (1) Production hardening of Railway env vars, (2) Toast migration to surface ~40 previously silent failures, (3) Backend + frontend admin system for managing users without going through Stripe checkout, (4) Doc versioning convention adopted across the project.

### Commits this session (2 major commits + docs commit, all pushed to main)

| Hash | Commit | Files |
|------|--------|-------|
| `28ead2d` | fix: surface silent errors via toast across 18 components | 18 |
| `3747eac` | feat: admin dashboard for user management and entitlement overrides | 19 |
| _(this commit)_ | docs: adopt SemVer-per-doc + CHANGELOG.md + frontmatter | 5 |

### Admin system shipped (commit 3747eac)

- **DB**: migration 027 (`users.is_admin` + `users.entitlement_overrides` JSONB), migration 028 (`admin_audit_log` table)
- **Backend**: `app/routers/admin.py` with `require_admin` dep, `app/services/audit_service.py`, `app/schemas/admin.py`. `entitlement_service.get_limits()` now merges per-user overrides over plan defaults.
- **Endpoints**: `GET /admin/users` (paginated, searchable, plan-filtered), `GET /admin/users/{id}` (detail with usage + effective limits), `PATCH /admin/users/{id}/plan` (free/basic/pro), `PATCH /admin/users/{id}/overrides` (set or clear per-key overrides), `PATCH /admin/users/{id}/admin` (grant/revoke admin, self-revoke blocked), `GET /admin/audit-log`
- **Frontend**: hidden `/admin` route lazy-loaded in App.tsx, Sidebar conditional Admin link, `pages/Admin.tsx` with tabbed nav, `components/admin/AdminUserTable.tsx` + `AdminUserDrawer.tsx` + `AdminAuditList.tsx`, `stores/adminStore.ts` (Zustand) for users + audit list + optimistic mutations
- **Audit log** captures every plan change, override edit, admin grant/revoke with before/after JSON details
- **First admin bootstrap**: SQL `UPDATE users SET is_admin = TRUE WHERE id = '<id from /auth/me>'` — must use the canonical id (`/auth/me` resolves duplicates by `clerk_user_id`, so updating by email can hit the wrong row)

### Toast migration shipped (commit 28ead2d)

- 18 files modified, +104/-49 lines
- ~40 silent failure sites converted: `console.error(...)` → `toast.error(extractError(err, fallback))`
- Removed inline error banners from Profile, CommentSection, StarRating, billing/UpgradeModal
- Kept SharedProject inline (full-page blocking errors — toast would dismiss after 4s leaving blank state)
- Kept Discovery auto-saves silent (retry every 30s anyway)
- Wrapped 2 unhandled `fetchPathway()` rejections in ModuleSession + PathwayExecute (404 silent, others toast)
- Added `toast.success()` on milestones: import, snapshot save/restore, share link create/revoke, comment post

### Railway env vars hardened

Set in Railway → backend service → Variables:
- `CORS_ORIGINS=["https://myide.ai","https://www.myide.ai"]` (JSON array)
- `CLERK_ISSUER=https://clerk.myide.ai` (no trailing slash)
- `CLERK_AUTHORIZED_PARTIES=["https://myide.ai","https://www.myide.ai"]` (JSON array)
- Webhook secrets verified: `CLERK_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`, `RESEND_WEBHOOK_SECRET`

Sign-in confirmed working post-hardening (GitHub OAuth + email code both verified).

### Doc versioning adopted

- **`DOC_VERSIONING.md`** (new): SemVer per doc, frontmatter format (Version + Last updated + CHANGELOG link), bump rules, CHANGELOG entry checklist
- **`CHANGELOG.md`** (new): Keep-a-Changelog format with backfilled entries for 2026-05-21 → 2026-05-23
- All versioned docs now carry frontmatter: CLAUDE.md, CONTEXT_HANDOFF.md, TODO.md, DOC_VERSIONING.md
- No automation — manual discipline + checklist. Pre-commit hooks deferred until drift becomes a problem.

### Earlier 2026-05-23 session (pre-admin)

Completed the comprehensive audit + fixed two user-reported mobile/UX bugs, with 2-agent verification per fix.

| Hash | Commit | Files |
|------|--------|-------|
| `9c5ef1c` | fix: transcript copy includes AI messages + add Save Place button | 2 |
| `5db42eb` | feat: close 5 critical spec gaps from audit | 6 |
| `253b30a` | feat: close all 8 remaining audit findings with 2-agent verification per fix | 16 |
| `fb1f1b8` | fix: mobile viewport conformance + surface PathwayReview errors | 24 |

### Tasks completed (15 from earlier session, plus admin + toast + docs)

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

- **Auth pipeline** — Clerk JWKS verification with issuer + audience + authorized-parties enforcement; INSERT ON CONFLICT race handling; svix-signed webhooks; migration 026/028 dedup history
- **Production hardening** — Railway env vars `CORS_ORIGINS`, `CLERK_ISSUER`, `CLERK_AUTHORIZED_PARTIES` all active; sign-in confirmed post-hardening
- **Admin dashboard** — `/admin` route gated by `users.is_admin`; plan/override/admin-flag mutations all working; audit log records every action
- **Entitlement system** — `get_limits()` merges per-user overrides over plan defaults; admins can comp users to pro or set per-key custom limits
- **Discovery SSE** — `done` event always fires (try/except wrapped), safety-net `onDone` in `useSSE`, anti-repetition CONVERSATION RULES injected, `sheet_update` fires BEFORE `done`
- **Error surfacing** — react-hot-toast globally available; ~40 previously silent failures now surface via `toast.error(extractError(err, fallback))` across 18 components
- **Backend ownership/entitlement gates** — Every project/session route filters by `user_id`; every creation path gated by plan limit
- **Migration chain** — Linear 001→028, all `down_revision` correct, all child-table names match models
- **Mobile viewport** — All 19 affected pages use `.h-dvh` + `.pb-mobile-nav`, Sidebar nav extends for safe-area, TopBar actions horizontally scrollable
- **CLAUDE.md** — Now at 2.0.0, all sections current; doc versioning system documented in DOC_VERSIONING.md
- **Partner styles** — 10 styles substantive (Behaviour/Questioning/Guardrails), default `strategist` consistent everywhere

---

## What Still Needs Your Action

### 🔐 Security hygiene (recommended but not blocking)

- **Rotate 3 webhook signing secrets** — `CLERK_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`, `RESEND_WEBHOOK_SECRET` were pasted in chat earlier this session. Roll each in its origin dashboard (Clerk/Stripe/Resend → Webhooks → Roll signing secret), then update Railway. Test after rotation with a "Send example" event.

### 🧹 Code follow-ups (low priority)

- **Other pages still use `setError` patterns** — Home (`createError`), SprintPlanner (`errorMessage`), Exports (already removed `packageError`), SharedProject (kept intentionally for full-page blocking errors). The remaining ones are non-blocking; toast-friendly to convert when convenient.
- **Duplicate `_partnerCache`** in Home.tsx and Inbox.tsx — could be hoisted to `lib/partnerCache.ts`. Currently independent fetches.
- **Cross-tab inbox badge sync** — Sidebar polls every 60s but doesn't listen to `storage` events. Adding ideas in tab A shows in tab B after up to 60s.
- **Orphan user row cleanup** — One known orphan row (no `clerk_user_id`) from the dedupe debug earlier. Safe to leave. Delete query in [duplicate-user-rows memory](.claude/memory/duplicate-user-rows.md) if desired.
- **Frontend admin tests** — No Vitest suite yet for the new admin store / drawer / table. Backend admin endpoints also lack pytest coverage. Worth adding when the test scaffolding for frontend lands.

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

## Database Migrations (linear chain: 001-028)

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
| 027 | Add `users.is_admin` (bool) + `users.entitlement_overrides` (JSONB) |
| 028 | Create `admin_audit_log` table (append-only admin action log) |

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

## Code Quality Snapshot (2026-05-23 — end of admin-system session)

- ✅ TypeScript: zero compilation errors
- ✅ Backend Python: syntax validated on all 11 admin-system files
- ✅ Migration chain: linear 001→028, all alembic IDs match
- ✅ Auth: race-handling consolidated with INSERT ON CONFLICT; production hardening active (issuer + audience + azp enforcement)
- ✅ SSE: always emits `done`, sheet_update fires before done
- ✅ Mobile: 19 pages use dynamic viewport + safe-area utilities
- ✅ Error UX: ~40 silent failures now surface via toast across 18 components; 2 `fetchPathway` callers wrapped
- ✅ Admin system: shipped with audit logging; entitlement overrides merge correctly with plan defaults
- ✅ Railway: all required env vars set; sign-in verified end-to-end
- ✅ Doc versioning: convention adopted, CHANGELOG seeded with recent history
- ⚠️ Webhook secrets: 3 exposed in chat earlier this session — rotate when convenient
- ⚠️ One orphan user row in DB (no clerk_user_id) — leftover from debug; safe to leave or delete
- ❌ Frontend tests: none exist (TypeScript build is the only verification)
- ❌ Backend admin endpoint tests: no pytest coverage yet
