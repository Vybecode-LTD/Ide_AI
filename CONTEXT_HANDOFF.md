# Ide/AI — Context Handoff Document

> **Version:** 3.1.0 · **Last updated:** 2026-05-23 · See [CHANGELOG.md](CHANGELOG.md)
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

## Current Session (2026-05-23) — Marathon Day

Single massive session that landed 10 commits across 5 major workstreams. Foundation is now ready for Phase 3 of the unified-Discovery overhaul.

### Commits this session (10, all pushed to main, in chronological order)

| Hash | What |
|------|------|
| `28ead2d` | fix: toast migration across 18 components (~40 silent errors surfaced) |
| `3747eac` | feat: admin dashboard at hidden `/admin` (users, plans, overrides, audit log) |
| `6599cd1` | docs: adopt SemVer-per-doc + CHANGELOG.md + frontmatter |
| `4032cbc` | docs: enforce doc-versioning via CLAUDE.md prominence + Stop hook |
| `ec1e0a2` | docs: refresh ROADMAP with shipped work + Up Next queue |
| `64a87bf` | feat: realtime inbox via SSE stream + Redis pub/sub (verified) |
| `e33c7a6` | fix: Discovery SSE always emits done; assistant msg persists independently |
| `fb840de` | feat(discovery v2): Phase 1 — module field schemas + up-front pathway assembly |
| `8cfc66a` | feat(discovery v2): Phase 2 — unified prompt + field_update event |
| `23f5e7d` | fix(discovery v2): Phase 2 hotfix — shape fix + race-safe upsert + type coercion |

### Most important things to know for the next session

**Discovery v2 overhaul is in flight** — Phases 1-2-hotfix-3-3hotfix all shipped today. Phase 4 is next. Two flow versions coexist:
- **v1 (legacy projects + template projects)** — `projects.flow_version = 'v1'`. Use Discovery → PathwayReview → PathwayExecute → per-module-sessions exactly as before. Untouched.
- **v2 (new non-template projects, default)** — `projects.flow_version = 'v2'`. Pathway assembled UP FRONT at project creation (POST /projects). Unified Discovery prompt funnels toward filling all module field schemas. New SSE event `field_update` carries per-module summary. After creation, Home shows a 2.2-second module-preview overlay listing what the AI will fill, then routes to /discovery.

**Phase 3 is shipped** (commit `94102cb`) + **Phase 3 hotfix shipped** (current commit) covering 5 audit-found bugs:
1. `setTimeout` leak in Home's preview-navigate (orphan timer no longer fires post-unmount)
2. Billing-success URL clean preserves `?category=...` (was stripped, causing flow loss)
3. Template projects now flagged `flow_version='v1'` (was defaulting to v2 with no pathway → Library/PathwayReview routing broke)
4. Library resume routing gates on `flow_version` — v2 projects always resume to `/discovery/{pid}`
5. PathwayReview redirects v2 projects to `/discovery/{pid}` on mount so deep-links don't drop users into legacy module sessions

**Where Phase 4 picks up — ProgressPanel for v2 Discovery:**
- Replace `DesignSheetPanel` on the right side of Discovery with a new `ProgressPanel` for v2 projects
- Subscribe to the `field_update` SSE event (already emitted by Phase 2 backend) for the live progress data
- Show overall % at top with the Proceed button (always available, warning chip if <80% required filled)
- Expandable per-module breakdown: filled / required-blank / optional-blank counts
- Replace the `sheet.confidence_score >= 70` Proceed trigger with a field-completion check
- Route Proceed to a temporary "Design Kit coming in Phase 5" placeholder (or directly to /exports for now) — Phase 5 builds the real `/design-kit/{projectId}` page

**Backend foundation is solid for v2:**
- Module library has 40 modules with 154 fields total (52 required, 102 optional), 6 modules flagged `has_output`
- `ai_service.build_unified_discovery_prompt` + `extract_module_fields` work end-to-end
- `discovery_service.apply_extracted_module_fields` uses race-safe ON CONFLICT upsert (migration 030)
- `_coerce_field_value` defends against AI returning wrong-shape values
- SSE done event always fires (Phase-pre robustness fix carried through)
- 5 audit-found bugs all closed via the Phase 3 hotfix commit

### Admin system live (commit 3747eac)

- Hidden `/admin` route gated by `users.is_admin`. Sidebar shows admin link automatically when flag is true.
- User search + plan toggle + entitlement overrides (Inherit/Unlimited/Custom per limit key) + grant-admin
- Append-only audit log on every action
- First admin bootstrap via SQL `UPDATE users SET is_admin = TRUE WHERE id = '<id from /auth/me>'` (use the id from /auth/me to avoid the duplicate-user-row gotcha — see `.claude/memory/duplicate-user-rows.md`)
- User confirmed admin works end-to-end

### Realtime inbox live (commit 64a87bf, verified)

- `GET /api/v1/inbox/stream` SSE endpoint backed by Redis pub/sub
- Channel per user: `inbox:user:{user_id}`. Published on POST/PROMOTE/DELETE inbox routes + inbound-email webhook.
- Frontend `inboxStore.connectStream()` opens an authenticated EventSource-style stream with exponential-backoff reconnect. Falls back to mount-time `refresh()` if Redis isn't configured (`REDIS_URL` empty → 503).
- Production env: Redis service attached, `REDIS_URL` set, sign-in verified, multi-tab realtime working

### Doc-versioning system live (commits 6599cd1 + 4032cbc)

- DOC_VERSIONING.md — SemVer per doc, root CHANGELOG, frontmatter format, 5-step checklist
- CHANGELOG.md — Keep-a-Changelog format, current up to today
- Stop hook at `.claude/hooks/check-doc-versioning.sh` nags if a commit touched `frontend/src/` or `backend/app/` without CHANGELOG.md
- Project memory entries for `admin-system`, `doc-versioning`, `duplicate-user-rows` so future sessions inherit the conventions

---

## Earlier 2026-05-23 work — Admin + Error UX + Initial Doc Versioning

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

- **Auth pipeline** — Clerk JWKS verification with issuer + audience + authorized-parties enforcement active in production
- **Production hardening** — Railway env vars set (CORS_ORIGINS, CLERK_ISSUER, CLERK_AUTHORIZED_PARTIES, REDIS_URL), sign-in + realtime inbox both verified end-to-end
- **Admin dashboard** — `/admin` route gated by `users.is_admin`; plan/override/admin-flag mutations all working; audit log records every action; user has tested it
- **Realtime inbox** — Redis pub/sub backed SSE stream verified delivering events under 1-2s; auto-reconnect + 503 fallback in place
- **Discovery SSE robustness** — `done` event always fires (try/except wrapped at every yield), assistant message persists in its own transaction (resume bug fixed), chip generator has a 3-item fallback chain
- **Discovery v1 (legacy projects)** — Unchanged: state machine stages → design-sheet extraction → sheet_update event → PathwayReview → PathwayExecute → per-module sessions
- **Discovery v2 backend foundation** — Up-front pathway assembly at project creation, unified prompt targeting all module field schemas, `field_update` SSE event, race-safe ON CONFLICT upsert, type coercion via `_coerce_field_value`
- **Module library** — 40 modules with 154 field schemas total (52 required, 102 optional), 6 modules flagged `has_output` for the Refresh affordance coming in Phase 5
- **Doc versioning** — DOC_VERSIONING.md convention + CHANGELOG.md + Stop hook all live; CLAUDE.md (2.4.1), CONTEXT_HANDOFF.md (3.0.0), TODO.md (2.0.0+), DOC_VERSIONING.md (1.1.0), ROADMAP.md (2.1.0) all carrying frontmatter
- **Backend ownership/entitlement gates** — Every project/session route filters by `user_id`; every creation path gated by plan limit
- **Migration chain** — Linear 001→030, all reversible cleanly
- **Mobile viewport** — All 19 affected pages use `.h-dvh` + `.pb-mobile-nav`
- **Error UX** — react-hot-toast wired; ~40 silent failures now surface via toast across 18 components

---

## What Still Needs Your Action

### 🚦 Phase 4 next steps (frontend ProgressPanel for v2 Discovery)

1. **New `ProgressPanel` component** at `frontend/src/components/discovery/ProgressPanel.tsx`. Replaces `DesignSheetPanel` on the right side of Discovery for v2 projects only.
2. **Extend `useSSE`** to handle the new `field_update` event type (currently silently dropped — `useSSE.ts:80-95`).
3. **Discovery.tsx branch**: if `project.flow_version === 'v2'`, render `ProgressPanel`; else keep `DesignSheetPanel`.
4. **Replace the Proceed-button trigger** at `Discovery.tsx:368` — for v2 use the `field_update` summary's `required_filled / required_total` ratio (e.g. show button always, with warning chip if <80%). Route to a placeholder `/design-kit/{projectId}` (404 for now until Phase 5 ships) OR keep routing to `/exports/{projectId}` as an interim.
5. Plumb `flow_version` into Discovery — currently not loaded. Either fetch project at mount or add to `/discovery/start` response.

### 🔐 Security hygiene (recommended but not blocking)

- **Rotate 3 webhook signing secrets** — `CLERK_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`, `RESEND_WEBHOOK_SECRET` were pasted in chat earlier today. Roll each in its origin dashboard, update Railway, test with "Send example".

### 🧹 Code follow-ups (low priority)

- **`Home.tsx createError` state** — convert to toast for consistency (one of the few remaining setError sites)
- **`SprintPlanner.tsx errorMessage` state** — currently kept alongside toast for sticky display during 60s+ generation; could simplify to toast-only
- **Duplicate `_partnerCache`** in Home.tsx and Inbox.tsx — hoist to `lib/partnerCache.ts`
- **Orphan user row** — one row with `is_admin=TRUE` but no `clerk_user_id` from the early-session debug. Safe to leave or `DELETE`.
- **Frontend tests** — none exist (TypeScript build is the only verification). Vitest scaffolding + first tests would be high-leverage.
- **Backend admin endpoint tests** — `require_admin` rejection, `update_user_plan` audit trail, `update_user_admin_flag` self-revoke block, entitlement override merge logic.

### 📋 Audit findings deferred from Phase 2 hotfix

- **Prompt size unbounded as modules scale** — currently 8-15 modules typical, ~150 lines of system prompt. Fine for now; revisit if Phase 5+ adds many more modules per pathway.
- **Discovery "Proceed" button still routes v2 to /pathway-review** — effectively unreachable since v2 doesn't update design_sheet (confidence_score stays at 0). Phase 4 will replace the trigger with a field-completion condition + route to the new design-kit page.

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
| 029 | Add `projects.flow_version` (legacy `v1` vs unified `v2` flow) |
| 030 | Phase-2 hotfix — backfill module_pathways.modules shape, dedup module_responses, UNIQUE(project_id, module_id) |

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

## Code Quality Snapshot (2026-05-23 — end of marathon session)

- ✅ TypeScript: zero compilation errors (last verified after toast migration + admin UI + realtime inbox)
- ✅ Backend Python: syntax validated on all 15+ files changed today
- ✅ Migration chain: linear 001→030, all reversible
- ✅ Auth: production-hardened with issuer + audience + azp enforcement; race-handling consolidated with INSERT ON CONFLICT
- ✅ SSE: always emits `done` (Phase-pre robustness fix); v2 emits `field_update` before done with default=str safety
- ✅ Mobile: 19 pages use dynamic viewport + safe-area utilities
- ✅ Error UX: ~40 silent failures now surface via toast across 18 components; 2 `fetchPathway` callers wrapped
- ✅ Admin system: live + user-tested; entitlement overrides merge correctly
- ✅ Realtime inbox: Redis pub/sub verified end-to-end in production
- ✅ Discovery v1: backward-compat fully preserved (verified by 2-agent audit)
- ✅ Discovery v2 backend: foundation solid (up-front assembly + unified prompt + race-safe upsert + type coercion + always-fires done)
- ✅ Railway: all env vars set including REDIS_URL
- ✅ Doc versioning: convention live + Stop hook nags on missing CHANGELOG
- ⚠️ Webhook secrets: 3 exposed in chat earlier — rotate when convenient
- ⚠️ One orphan user row in DB (no clerk_user_id) — leftover from debug
- ⚠️ Phase 3 frontend not yet started — v2 projects can be created but currently routed through the v1 UI
- ❌ Frontend tests: none exist
- ❌ Backend admin endpoint tests: no pytest coverage yet
- ❌ Discovery v2 tests: zero coverage on the new prompt builder, extractor, upsert path
