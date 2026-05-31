# Ide/AI — Context Handoff Document

> **Version:** 3.13.1 · **Last updated:** 2026-05-31 · See [CHANGELOG.md](CHANGELOG.md)
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

## Current Session (2026-05-31) — Notion SHIPPED to production (merged + deployed + OAuth connect verified)

The Notion integration went live. Reviewed the branch for correctness, verified green, pushed it (it had been **local-only**), **merged to `main`** (`--no-ff`, merge commit **`32ec540`**), pushed → Railway auto-deployed both services. Guided the Notion + Railway setup, then confirmed the live OAuth **connect** works.

### What happened
- **Pre-merge review** — read `notion_service.py`, the 4 routes in `integrations.py`, `test_notion_integration.py`, both frontend components, `config.py` (the `NOTION_*` settings exist), `encryption.py` (`INTEGRATION_TOKEN_KEY` required for token storage). All sound; both components confirmed wired into `Settings.tsx` (L242) + `DesignKit.tsx` (L784).
- **Verified green** — backend **270 collected / 265 pass · 1 skip · 4 deselected** (`-k "not PromptComposition"`); frontend **37/37**; `tsc -b --noEmit` + ESLint clean.
- **Branch pushed** to origin (was local-only), then **merged `--no-ff` → `32ec540` → pushed `main`** (`06901cf..32ec540`). Railway auto-deployed.
- **Env set in Railway** (by the user): `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, `NOTION_REDIRECT_URI` (= `https://backend-production-9c212.up.railway.app/api/v1/integrations/notion/callback`), `INTEGRATION_TOKEN_KEY` (fresh Fernet key).
- **Live OAuth connect verified** by the user.

### Gotchas / decisions (READ THESE before touching Notion or Railway env)
- **First connect click returned "not found"** — the Railway env/deploy hadn't fully propagated; a **retry worked**. Diagnosed by probing the prod callback (`GET …/integrations/notion/callback` → `307 → /settings?notion=error`), which proved the new backend was already live (route exists) and ruled out a missing-route 404. **Lesson: right after a Railway env change + deploy, the first OAuth click can transiently fail — retry before debugging.**
- **`INTEGRATION_TOKEN_KEY` is now set and MUST NOT be rotated** — it Fernet-encrypts stored OAuth tokens; rotating it makes every stored token unreadable (forces all users to reconnect). `encryption.py` raises if it's unset.
- **`SHARE_ACCESS_SECRET` intentionally left unset** — both OAuth `state` signing and share-viewer tokens fall back to `CLERK_SECRET_KEY` (`integrations.py` L226, `sharing.py` L36). No new secret needed.
- **A stray `SECRET_KEY` exists in Railway but is UNUSED** — this app reads `CLERK_SECRET_KEY` / `STRIPE_SECRET_KEY` / `SHARE_ACCESS_SECRET` / `INTEGRATION_TOKEN_KEY`, never a bare `SECRET_KEY`. Harmless; leave it.
- **Notion requires a PUBLIC integration** (not Internal) — Internal has no OAuth client. The "associated workspace" at creation is only the admin home; Public is what lets *any* user connect *their own* workspace via OAuth. Redirect URI + `client_id`/secret live in the integration's **Configuration** tab.

### Residual (non-blocking)
- ⏳ **Confirm the end-to-end push** — Design Kit → Push to Notion → page renders in Notion. The **connect** half was verified live; the **push** half is deployed + tested (24 tests) but not explicitly re-confirmed by the user this session.
- ✅ **Merged branch deleted** — `feature/notion-integration` removed from local + `origin` (2026-05-31), after confirming it was fully merged into `32ec540`.
- Carryovers: SAST-H1 (rate-limit sharing endpoints), DEP-H1 (js-cookie CVE upstream), stale `AGENTS.md`, PG-only upsert test (needs a Postgres harness).

### Health
**Backend 270 collected across 11 files — 265 passed · 1 skipped (PG-only upsert) · 4 deselected (need live Anthropic).** Frontend 37/37 (5 files). `tsc` + ESLint clean. **Production: Notion live (merged `32ec540`, deployed, OAuth connect verified).**

---

## Previous Session (2026-05-30) — Notion integration built (OAuth + push design kit)

First live external integration — built on branch **`feature/notion-integration`** (commit `d22dbac`). **Merged to `main` as `32ec540` on 2026-05-31** (see Current Session above for the merge/deploy/verify).

### What shipped
- **Backend** `app/services/notion_service.py` — OAuth helpers (`is_configured` / `build_authorize_url` / `exchange_code_for_token`), a **pure** `render_design_kit_blocks()` turning the unified v1/v2 artifact context into Notion blocks, and REST IO (`create_design_kit_page` w/ 100-child batching, `list_accessible_pages`). Four routes in `integrations.py`: `notion/authorize` (signed-`state` JWT), `notion/callback` (**public** — auth in the verified state; exchanges code → Fernet-encrypted token → 302 to `/settings?notion=…`), `notion/pages`, `notion/push/{project_id}`. Three `NOTION_*` config vars.
- **Frontend** `components/integrations/NotionConnectCard.tsx` (Settings) + `NotionPushButton.tsx` (Design Kit, inline modal matching the ShareDialog pattern — no shared Modal exists). One-line drop-ins into `Settings.tsx` and `DesignKit.tsx`.
- **Tests** `backend/tests/test_notion_integration.py` (25 — pure rendering, OAuth-state mint/verify/tamper/scope, all 4 routes; only the network/config edges mocked).

### Key decisions / gotchas
- **Docs oversold the starting point**: ROADMAP claimed "OAuth infrastructure in place" and CLAUDE listed `/integrations/{provider}/auth|callback|push` — none existed. Only Fernet storage + basic CRUD were real. Near-greenfield build; feature #24 in CLAUDE.md corrected.
- **OAuth `state`** reuses the share-token signing pattern (HS256; secret falls back SHARE_ACCESS_SECRET → CLERK_SECRET_KEY) — no new required secret.
- **Callback is public** (a browser redirect carries no Clerk header) — security rides entirely in the signed, scoped, 10-min-TTL `state`.
- **Graceful when unconfigured**: no `NOTION_*` env → `is_configured()` False → `/authorize` 503 + Settings shows "Not available yet". Safe to merge dark.

### Activation — ✅ COMPLETED 2026-05-31
1. ✅ Registered a **public** integration at notion.so/my-integrations.
2. ✅ Set Railway backend env: `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, `NOTION_REDIRECT_URI` (the callback URL) + `INTEGRATION_TOKEN_KEY`.
3. ✅ Merged `feature/notion-integration` → `main` (`32ec540`); Railway auto-deployed; OAuth **connect** verified live (end-to-end **push** pending final confirmation).

### Health (at build time, 2026-05-30)
**Backend 270 collected across 11 files** — 265 passed · 1 skipped (PG-only upsert) · 4 deselected (need live Anthropic). Frontend 37/37, `tsc` clean, ESLint clean. _(Now merged + deployed — see Current Session above.)_

---

## Previous Session (2026-05-30, earlier) — Discovery v2 SSE streaming tests

Closed the last big backend coverage gap. Added **`backend/tests/test_discovery_sse.py`** (17 tests: 16 pass + 1 documented skip) for the two SSE streaming routes every prior suite skipped — `POST /discovery/{id}/init` and `POST /discovery/{id}/message`. **Test-only; no application logic changed.** Committed to `main` as `06901cf`.

### Approach
- **Mock boundary = the AI calls only.** Patched `ai_service.stream_response` (async token generator), `ai_service.generate_quick_chips`, `ai_service.extract_module_fields`, and `discovery_service.extract_sheet_fields` (patched where it is *used* — `discovery_service` imports the name directly). Everything else runs for real: flow-version branching, the prompt builders (they never touch the network), message persistence, the v1 design-sheet update, field-summary aggregation, and the SSE event assembly itself. So these are true integration tests of the routes, not unit tests of a mock.
- **Sync `TestClient`, not async httpx.** An early async-httpx rewrite failed: pytest is in `asyncio_mode = STRICT`, so bare `async def test_` methods aren't collected. The sync Starlette `TestClient` drives the SSE generator (incl. its async DB IO) fine here.

### What the tests prove
- init streams tokens in order, persists the assistant greeting, and **always** ends with a single `done` carrying chips; rejects an already-initialized session (400) and a missing one (404).
- message: v2 emits `field_update` (+ aggregate `summary`) and v1 emits `sheet_update` — each **before** `done`; never both. The two flows are driven by `project.flow_version`.
- v2 vs v1 **system prompts genuinely differ** (the unified prompt's `MODULES IN THIS DESIGN KIT` marker is present for v2, absent for v1), captured off the stream mock.
- extraction raising mid-stream still yields a `done` sentinel with chips (the discovery.py try/except hardening).

### Known limit (one documented skip)
- `test_extraction_upsert_writes_new_field` is `@pytest.mark.skip` — it exercises `apply_extracted_module_fields`' PostgreSQL `INSERT ... ON CONFLICT ... responses || EXCLUDED.responses` upsert, whose `||` is JSONB-merge in Postgres but string-concat in SQLite. Un-skip when a PG-backed harness (e.g. testcontainers) lands. Summary aggregation is instead proven SQLite-safely by seeding a value through the real PATCH endpoint and asserting the SSE summary reflects it.

### Health
**Backend 246 collected across 10 files** — 241 passed · 1 skipped (PG-only upsert) · 4 deselected (`PromptComposition`, needs live Anthropic). Frontend 37/37 (5 files). No app code touched, so no `tsc`/vitest impact. Production unchanged (both Railway services green).

---

## Previous Session (2026-05-30) — Doc governance + deploy fixes + production CSP incident

Long session: vendored/reconciled the Claude-Kit directive system into the repo, fixed two deploy-blockers, resolved a two-part production outage, and a Home UX tweak. **8 commits, all pushed; production verified healthy (sign-in / admin / profile work live).**

### Commits on `main`

| Hash | What |
|------|------|
| `6812a87` | Reconcile Claude-Kit doc directive to root-level SemVer-per-doc (CLAUDE.md "Doc system scope" override; DOCUMENTATION_MANAGER.md remapped — no `docs/` tree) |
| `0f96d48` | Correct repo URL → `github.com/Vybecode-LTD/Ide_AI` (was stale PromptMonster-Media-Ltd) |
| `f7eff4c` | Vendor + `@include` the binding directives (track DEBUG_PROTOCOL / VERSION_CONTROL / SEO_OPTIMIZATION / seo-research-catalog / TESTING_PROCEDURES / SOFTWARE_RELEASE / _CLAUDE-KIT-README; TESTING scoped to Python+React + no-preview; SOFTWARE_RELEASE → N/A stub) |
| `7ce7148` | **Fix Railway backend build** — regenerate `backend/poetry.lock` (a `dev` group was added to pyproject.toml without re-locking) |
| `a6862e4` | VERSION_CONTROL pre-commit gate now mandates re-locking after a manifest edit |
| `0e5c7c7` | **Fix prod white-screen** — add `https://clerk.myide.ai` to the CSP (Clerk prod custom domain) |
| `c826ad5` | **Fix missing name/Admin link** — add backend ORIGIN to CSP connect-src (path blocked `/api/v1/*`) |
| `a21af70` | Home: move Start Discovery CTA above the optional template grid |

### ⚠️ Production CSP incident (resolved) — read before touching `frontend/Caddyfile`

The day's first push deployed the SAST-M2 CSP (from `544bb2f`). The site then white-screened on a spinner; after the first fix it lost the user's name + Admin link. **Root cause was the CSP, NOT the key rotation.** Two bugs, both fixed in `frontend/Caddyfile` with guard comments:
1. CSP allowed only Clerk's **dev** domain `*.clerk.accounts.dev`; production's Clerk Frontend API is the **custom domain `clerk.myide.ai`** (the `pk_live_…` key decodes to it). Clerk's SDK was blocked → infinite spinner. **`clerk.myide.ai` must stay in script-src / connect-src / img-src / frame-src.**
2. CSP `connect-src` listed the backend with its `/api/v1` **path**; CSP exact-matches paths with no trailing slash, so `/api/v1/auth/me` (loads the user + is_admin) and every sub-path call were blocked → `authStore.user` empty. **The backend ORIGIN with no path must stay in connect-src.**
Diagnosed by reading the live CSP header + decoding the deployed publishable key. Lesson: a green Railway build ≠ a working app — run the smoke test.

### Other
- **Secrets rotated + verified** — user rotated all 3 webhook signing secrets AND the API keys (Clerk/Stripe/Resend), updated Railway env, sign-in confirmed end-to-end. The old "rotate secrets" P0 is done.
- **Doc governance settled** — root-level docs + SemVer-per-doc (DOC_VERSIONING.md) is binding. Kit directives are tracked + `@include`d in CLAUDE.md; the reconciled DOCUMENTATION_MANAGER.md **forbids** a `docs/` managed-doc tree / `initialize project docs`. The global `session-orchestrator` skill stays global; if used it must target these root docs.
- **Lockfile discipline** — any manifest edit must include its re-locked lockfile in the same commit (now in VERSION_CONTROL.md).

### Health
Backend 229/229 (9 files), frontend 37/37 (5 files), `tsc -b --noEmit` clean. No backend logic changed this session. Both Railway services green; production smoke-verified.

> _Note: the older "What's Working Today" / "Code Quality Snapshot" sections below still cite 215/31 test counts from earlier sessions — current is 229/37 (see CLAUDE.md). Minor stale-count drift, left as-is to keep this handoff focused._

---

## Previous Session (2026-05-28) — Doc reconciliation + CI + asset commit

Follow-up to the 12-task Codex alignment audit. Committed CI workflow and OG image source, then ran a full documentation audit verifying every claim against disk state.

### What shipped this session

- **`.github/workflows/test-pipeline.yml`** — GitHub Actions CI pipeline with auto-detect for Python/React/C++/.NET stacks, security scanning (Gitleaks + CodeQL), and deploy gate.
- **`frontend/public/og-image.psd`** — OG image source file (7MB PSD). Still needs export to PNG (1200×630).
- **CLAUDE.md v2.11.0** — 3 discrepancies fixed:
  1. Added `admin_audit_log.py` to models listing (existed on disk, missing from docs)
  2. Expanded types/ listing from 4 to 8 files (blocks.ts, export.ts, modulePathway.ts, pipeline.ts were missing)
  3. Fixed module count: "47 modules" → "40 modules" (Feature 14)
- **CONTEXT_HANDOFF.md v3.9.0** — updated for this session.
- **TODO.md v3.8.0** — cleaned stale P0 items, updated og-image status.

### Commits

| Hash | What |
|------|------|
| `544bb2f` | feat: v2 artifact bridge, billing hardening, security fixes, full doc audit |
| `8f61cfa` | chore: CI workflow, og-image source, doc reconciliation |
| `20feec4` | docs: reconcile ROADMAP.md — fix stale counts and completed items |

### Test results
- **Backend**: 229/229 pass (9 files). **Frontend**: 37/37 pass (5 files). **TypeScript**: clean.

### Security status
- **SAST-H2 fixed**: OpenAPI docs disabled in production.
- **SAST-M1 fixed**: Stripe error responses sanitized.
- **SAST-M2 fixed**: CSP header added to Caddyfile.
- **SAST-H1 (open)**: No rate limiting on sharing endpoints — needs `slowapi`.
- **SAST-M3 (by design)**: CORS defaults to localhost in dev; production uses `CORS_ORIGINS` env var.
- **DEP-H1 (upstream)**: js-cookie CVE — transitive from `@clerk/shared`.

### Pending
- **Push to main** — 3 commits ahead of origin. Push triggers Railway auto-deploy.
- **Rotate 3 webhook secrets** — CLERK, STRIPE, RESEND.
- **Export og-image.psd → og-image.png** (1200×630).
- **5-minute production smoke test** after Railway deploy.

---

## Previous Session (2026-05-25) — Production bug-fixing marathon (7 fixes + 38 tests)

User live-tested the Railway deployment and reported 7 production bugs across 2 sub-sessions. All fixed, regression-tested (188 backend + 31 frontend + 0 TS errors), committed and pushed.

**Sub-session 1 — Initial 3 bugs + chip overhaul + PDF fix:**
1. **Mobile overflow** — AI messages/chips went off-screen on phones (flex `min-width: auto` default). Fix: `min-w-0` + `overflow-x-hidden` on Discovery flex containers.
2. **Premature proceed button** — "Proceed to Design Kit" clickable at any %. Fix: gated on field completion percentage.
3. **Extraction stalling at ~85%** — Two root causes: full conversation history diluted extraction signal + conservative extraction rules. Fix: windowed to last 8 messages (`_EXTRACTION_WINDOW`) + aggressive extraction + "STILL MISSING" section.
4. **Chip relevance overhaul** — Quick-reply chips showed generic "Yes exactly"/"Not quite" instead of matching the AI's question. Fix: replaced keyword-bucket fallback with AI-powered contextual chip generation via `_generate_chips_from_question()`. Added generic-chip blocklist filter. New `__type_your_answer__` sentinel (`CHIP_TYPE_YOUR_ANSWER`) renders as an amber non-clickable indicator in the frontend. FORBIDDEN chip list added to all 4 prompt variants.
5. **PDF transcript export "Network Error"** — Unicode chars in `Content-Disposition` headers corrupted HTTP responses. Fix: `safe_filename_slug()` utility applied across all 7 export endpoints + try/except on PDF generation.

**Sub-session 2 — Two more bugs found by user during live test:**
6. **Proceed button falsely enabled at 85%** — Root cause: `compute_field_summary()` counted fields as "filled" based on key existence alone — empty strings, `None`, empty lists/dicts all inflated the count. Fix: added `_has_value()` validator in `discovery_service.py` that requires meaningful non-empty content. Additionally changed the proceed button to gate on `overall_percent >= 100` (matching the visible header badge) instead of required-only percentage, eliminating the confusing mismatch.
7. **Design Kit "Continue Discovery" button cut off on mobile** — Header buttons were in a non-wrapping `flex` row that overflowed on narrow screens. Fix: refactored header to stack vertically on mobile (`flex-col` → `md:flex-row`), added `flex-wrap` to action buttons, added sticky bottom bar for "Continue Discovery" CTA on mobile (positioned at `bottom-16` above the nav), added `pb-28` extra bottom padding to prevent content occlusion.

### Commits this session

| Hash | What |
|------|------|
| `bb3c5bf` | fix: 3 production bugs — mobile overflow, proceed gate, extraction stalling |
| `da31ad8` | fix: overhaul chip relevance — AI-powered fallback + type-your-answer indicator |
| `8eaf247` | fix: PDF transcript export — safe filename slugs across all 7 export endpoints |
| `806dd1d` | test: 30 regression tests for chip relevance + safe filename slugs |
| `8168282` | docs: bump CLAUDE.md 2.9.3 — test count 180, last completed task |
| _(uncommitted)_ | fix: proceed button _has_value + Design Kit mobile layout + 8 tests + doc update |

### Previous sessions

- **2026-05-24**: Admin tests (27) + toast cleanup (Home/SprintPlanner). Phase 6 mini-Discovery scoped sessions + audit hardening (16 regression tests).
- **2026-05-23 marathon**: Phases 1-4 + audit closure + integration tests + doc lockdown. 11+ commits across 6 workstreams.

### Most important things to know for the next session

**All phases shipped + production hardened.** The codebase is in a stable, tested state. All user-reported bugs from live testing are fixed. The main outstanding items are deployment verification and security hygiene.

**Discovery v2 overhaul is COMPLETE** — all 6 phases shipped. Two flow versions coexist:
- **v1 (legacy projects + template projects)** — `projects.flow_version = 'v1'`. Use Discovery → PathwayReview → PathwayExecute → per-module-sessions exactly as before. Untouched.
- **v2 (new non-template projects, default)** — `projects.flow_version = 'v2'`. Pathway assembled UP FRONT at project creation (POST /projects). Unified Discovery prompt funnels toward filling all module field schemas. SSE event `field_update` carries per-module summary. Right side panel shows live progress meter (ProgressPanel). Proceed button routes to `/design-kit/{id}`. Design Kit page shows all modules, Edit/Refresh/Add Modules. "Continue Discovery" button launches a scoped mini-Discovery for modules with unfilled required fields.

**Phase 4 + audit closure shipped** (this commit) — full frontend + backend parity for v2, plus all actionable audit findings resolved:

Phase 4 frontend (originally):
1. `ProgressPanel` on right side of Discovery for v2 — overall %, expandable per-module breakdown, recent-update accent
2. `useSSE` extended with `onFieldUpdate` callback + exported types
3. `Discovery.tsx` branches right panel + mobile badge + Proceed gate on `flow_version`
4. v2 Proceed routes to `/exports/{id}` with field-completion gate
5. Module-preview overlay a11y (role/labelledby/describedby/Esc/focus/mobile max-h)

Audit closure (14 items addressed):
- **H1** — `projects.py` downgrades v2→v1 when assembly skipped (no stranded users)
- **H2** — `PathwayExecute.tsx` v2 redirect (defense-in-depth)
- **M6** — `GET /discovery/{session_id}/field-summary` endpoint + frontend hydration on mount
- **M3** — `build_unified_greeting_prompt` for v2 init (references assembled modules)
- **M7** — `_coerce_field_value` drops now logged with full context
- **M1** — extraction prompt instructs dict fields to return whole object
- **M8** — Proceed gate uses `total_fields > 0` (handles all-optional pathways)
- **M2/L3** — Stage UI hidden for v2 (TopBar subtitle + StagesStepper + mobile indicator)
- **M4** — `loadSheet()` skipped for v2 (consolidated bootstrap effect)
- **M5/L2** — ProgressPanel expanded set capped at 3 modules (FIFO)
- **L1** — `recentUpdates` highlight fades after 8s
- **L5** — `_reset_module_library()` test hook
- **I4** — new `test_discovery_v2.py` with 35 tests (76 total backend tests, all passing)
- **Defensive bonus** — `apply_extracted_module_fields` now rejects unknown field keys (caught by the new tests)

**Phase 5 + 6 COMPLETE + AUDIT-HARDENED — Design Kit + scoped mini-Discovery:**
- Design Kit at `/design-kit/{projectId}` — v2 Proceed destination. Per-module Edit with type-aware inputs, Refresh output on `has_output` modules, Add Modules picker.
- Phase 6: `scope_module_ids` JSONB on `discovery_sessions` (migration 031). Scoped sessions filter init/message/field-summary to only targeted modules. "Continue Discovery (N)" button in DesignKit navigates to `/discovery/:projectId?scope=mod1,mod2,...`.
- **Phase 6 audit hardening:** 6-agent audit caught 6 HIGH-severity issues (library subquery scope leak, orphan cleanup scope leak, no scope ID validation, missing frontend dep, DesignKit unfilled-check logic, scoped sessions on v1 untested). All fixed. `POST /discovery/start` now validates scope IDs against the pathway and rejects scoped sessions on v1 projects. Empty `scope_module_ids=[]` normalized to `None` via Pydantic validator.
- **Test coverage: 123 backend + 31 frontend.** 16 new regression tests: 4 audit-driven integration (empty scope, invalid IDs, v1 rejection, multi-module), 6 integration regression (library isolation, resume survival, v1 unaffected, mixed IDs, null scope, full summary), 6 service-layer regression (resume, scoped-create, scoped-doesn't-pollute, get-latest-ignores, orphan-skip, force-new).

**Backend foundation is solid for v2:**
- Module library has 40 modules with 154 fields total (52 required, 102 optional), 6 modules flagged `has_output`
- `ai_service.build_unified_discovery_prompt` + `extract_module_fields` work end-to-end
- `discovery_service.apply_extracted_module_fields` uses race-safe ON CONFLICT upsert (migration 030)
- `_coerce_field_value` defends against AI returning wrong-shape values
- SSE done event always fires (Phase-pre robustness fix carried through)
- All 5 Phase-3 audit-found bugs closed via the Phase 3 hotfix commit
- Frontend ProgressPanel hydrates from `field_update` SSE — TypeScript build clean (Phase 4)

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
- **Discovery SSE robustness** — `done` event always fires (try/except wrapped at every yield), assistant message persists in its own transaction (resume bug fixed), chip generator has a 4-stage pipeline: (1) parse `[CHIPS:]` tag → (2) "X, Y, or Z" pattern → (3) AI-powered contextual generation → (4) `__type_your_answer__` sentinel fallback
- **Quick-reply chip relevance** — Generic-chip blocklist filter rejects "Yes exactly"/"Not quite" etc. AI-powered `_generate_chips_from_question()` generates contextual options matching the AI's actual question. FORBIDDEN chip list in all 4 prompt variants. Frontend renders `__type_your_answer__` sentinel as amber non-clickable indicator.
- **Discovery v1 (legacy projects)** — Unchanged: state machine stages → design-sheet extraction → sheet_update event → PathwayReview → PathwayExecute → per-module sessions
- **Discovery v2 backend** — Up-front pathway assembly at project creation, unified prompt targeting all module field schemas, `field_update` SSE event, race-safe ON CONFLICT upsert, type coercion via `_coerce_field_value`, extraction windowed to last 8 messages (`_EXTRACTION_WINDOW`)
- **Discovery v2 frontend** — `ProgressPanel` swaps for `DesignSheetPanel` on v2 projects; mobile badge + Proceed button gate also branch on `flow_version`; v2 Proceed routes to `/design-kit/{id}` with `overall_percent >= 100` gate; `min-w-0` + `overflow-x-hidden` on all flex containers for mobile safety
- **Field summary accuracy** — `compute_field_summary()` uses `_has_value()` validator that rejects empty strings, None, empty lists/dicts, whitespace-only — no more inflated counts from AI extraction writing empty placeholders
- **Design Kit mobile** — Header stacks vertically on mobile, buttons wrap, sticky bottom bar for "Continue Discovery" CTA above the nav, `pb-28` prevents content occlusion
- **Export safety** — `safe_filename_slug()` strips Unicode from `Content-Disposition` headers across all 7 export endpoints; try/except on PDF generation returns proper 500
- **Module-preview overlay a11y** — `role="alertdialog"`, labelledby/describedby, Esc-to-skip, focus-on-mount, mobile max-h fix
- **Audit-closure additions** — `GET /discovery/{session_id}/field-summary` endpoint, `build_unified_greeting_prompt` (v2-aware init), `_coerce_field_value` drop logging, defensive unknown-field-key rejection, ProgressPanel expanded-set cap (FIFO 3), recentUpdates 8s fade, stage UI hidden for v2, loadSheet skipped for v2, `_reset_module_library` test hook
- **Module library** — 40 modules with 154 field schemas total (52 required, 102 optional), 6 modules flagged `has_output`
- **Backend test coverage** — **215/215 pass** across 8 test files. 75 tests on v2 (41 service-layer + 34 HTTP-level), 31 module completion, 27 admin, 38 regression (chips/slug/transcript/field-summary), 9 entitlements, 28 partner styles, 4 discovery resume, plus 3 misc.
- **Doc versioning** — DOC_VERSIONING.md convention + CHANGELOG.md + Stop hook all live; CLAUDE.md (2.9.4), CONTEXT_HANDOFF.md (3.6.0), TODO.md (3.6.0), DOC_VERSIONING.md (1.1.0), ROADMAP.md (2.3.0) all carrying frontmatter
- **Backend ownership/entitlement gates** — Every project/session route filters by `user_id`; every creation path gated by plan limit
- **Migration chain** — Linear 001→030, all reversible cleanly
- **Mobile viewport** — All 19 affected pages use `.h-dvh` + `.pb-mobile-nav`
- **Error UX** — react-hot-toast wired; ~40 silent failures now surface via toast across 18 components

---

## What Still Needs Your Action

### ✅ P0 — all cleared (2026-05-30)

The blockers from the 2026-05-28 handoff are **done**: all commits pushed + deployed, `og-image.png` created, secrets rotated (webhook signing **and** API keys, all 3 providers) + verified, and production smoke-verified (sign-in / admin / profile work live after the CSP incident fix). **No P0 blockers remain.**

**Still open (non-blocking):**
- ⏳ **Confirm the Notion end-to-end push** — Design Kit → Push to Notion → page renders in Notion. OAuth **connect** was verified live this session; the **push** is deployed + tested (24 tests) but not explicitly live-confirmed.
- ✅ **Deleted the merged `feature/notion-integration` branch** (local + `origin`, 2026-05-31) — was fully merged as `32ec540`.
- **SAST-H1** — rate limiting on anonymous sharing endpoints (`/sharing/public/{token}/comments|ratings`); install `slowapi`.
- **DEP-H1** — js-cookie CVE, transitive from `@clerk/shared` (upstream).
- **AGENTS.md is stale** — wrong drive path / "React 18" / "Codex API" / old repo URL; reconcile-or-delete.
- **PG-only upsert test** — `apply_extracted_module_fields` ON CONFLICT path needs a Postgres-backed harness (testcontainers); currently the single skipped backend test.
- ~~Discovery v2 SSE streaming tests~~ — **DONE 2026-05-30** (`test_discovery_sse.py`, on `main`).

### 🔐 Security hygiene (recommended but not blocking)

- ~~Rotate 3 webhook signing secrets~~ — **DONE 2026-05-30** (webhook signing secrets **and** API keys for all 3 providers rotated + verified).
- **`INTEGRATION_TOKEN_KEY` is now set in Railway (2026-05-31) — do NOT rotate it** (would make stored Notion OAuth tokens unreadable; users would have to reconnect).
- **Orphan user row** — one DB row with `is_admin=TRUE` but no `clerk_user_id` from early debug. Safe to leave or `DELETE`.

### 🧹 Code follow-ups (low priority)

- **`Home.tsx createError` state** — convert to toast for consistency (one of the few remaining setError sites)
- **`SprintPlanner.tsx errorMessage` state** — currently kept alongside toast for sticky display during 60s+ generation; could simplify to toast-only
- **Duplicate `_partnerCache`** in Home.tsx and Inbox.tsx — hoist to `lib/partnerCache.ts`
- **Orphan user row** — one row with `is_admin=TRUE` but no `clerk_user_id` from the early-session debug. Safe to leave or `DELETE`.
- **Frontend tests** — 37 Vitest tests across 5 files (`extractError`, `fieldValue`, `inboxStore`, `useSSE`, `ProgressPanel`). DesignKit edit/save flow + the new Notion components (`NotionConnectCard`, `NotionPushButton`) still untested (verified via `tsc` + live smoke only).
- ~~Backend admin endpoint tests~~ — **DONE** (`test_admin.py`, 27 tests: require_admin gate, plan update + audit trail, self-revoke block, override merge).

### 📋 Audit findings deferred from Phase 2 hotfix

- **Prompt size unbounded as modules scale** — currently 8-15 modules typical, ~150 lines of system prompt. Fine for now; revisit if Phase 5+ adds many more modules per pathway.
- ~~Discovery "Proceed" button still routes v2 to /pathway-review~~ — **closed in Phase 4**. v2 Proceed now routes to `/exports/{id}` with a field-completion gate. Phase 5 swaps the destination to the new `/design-kit/{id}` page.

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

## Database Migrations (linear chain: 001-032)

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
| 031 | Add `sessions.scope_module_ids` (JSONB, nullable) for mini-Discovery scoped sessions |
| 032 | Add Stripe subscription state columns (`stripe_subscription_id`, `subscription_status`, `subscription_price_id`, `subscription_current_period_end`) |

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

**Frontend tests** — 37 tests across 5 files via Vitest. Run: `npx.cmd vitest run` from `frontend/`. TypeScript verification: `npx.cmd tsc -b --noEmit`.

---

## Regression Test Matrix (what protects what)

For each major code path, the test file(s) that prove it works. Use this when changing the underlying code: if you touch a path, the protecting test should still pass; if you can't make it pass, the test or the code is wrong.

| Code path | Protected by | Count |
|---|---|---|
| v1 Discovery state machine + resume | `test_discovery_resume.py` | 4 |
| v2 unified discovery prompt | `test_discovery_v2.py::TestBuildUnifiedDiscoveryPrompt` | 3 |
| v2 unified greeting prompt | `test_discovery_v2.py::TestBuildUnifiedGreetingPrompt` | 3 |
| v2 field extraction + type coercion | `test_discovery_v2.py::TestCoerceFieldValue` + `TestApplyExtractedModuleFields` | 14 |
| v2 summary aggregation | `test_discovery_v2.py::TestComputeFieldSummary` | 4 |
| v2 pathway decoration (list[str] + legacy list[dict]) | `test_discovery_v2.py::TestLoadDecoratedPathwayModules` | 4 |
| `_reset_module_library` test hook | `test_discovery_v2.py::TestResetModuleLibrary` | 2 |
| v2 session resume + scope isolation | `test_discovery_v2.py::TestSessionResumeRegression` | 6 |
| H1 fix (v2 → v1 downgrade on failed assembly) | `test_discovery_v2_integration.py::TestCreateProjectH1` | 5 |
| M6 endpoint (field-summary) | `test_discovery_v2_integration.py::TestFieldSummaryEndpoint` | 4 |
| Phase 3 hotfix (template projects = v1) | `test_discovery_v2_integration.py::TestTemplateFlowVersion` | 1 |
| Library resume routing v1/v2 | `test_discovery_v2_integration.py::TestLibraryResumeRouting` | 2 |
| Discovery session-start + ownership | `test_discovery_v2_integration.py::TestDiscoveryStartV2` | 2 |
| ProjectRead shape (frontend type dep) | `test_discovery_v2_integration.py::TestProjectReadShape` | 1 |
| Design Kit endpoints (GET + PATCH) | `test_discovery_v2_integration.py::TestDesignKitEndpoint` | 5 |
| Refresh output + Add Modules | `test_discovery_v2_integration.py::TestRefreshOutput` + `TestAddModules` | 6 |
| Phase 6 scoped sessions (create, isolation, field-summary) | `test_discovery_v2_integration.py::TestScopedSessions` | 8 |
| Phase 6 audit regression (library, resume, v1, validation) | `test_discovery_v2_integration.py::TestAuditFixRegressions` | 6 |
| Entitlement gates | `test_entitlements.py` | 9 |
| Partner styles + prompt composition | `test_partner_style.py` | 28 |
| Admin: require_admin gate | `test_admin.py::TestRequireAdmin` | 3 |
| Admin: user list (paginate/search/filter) | `test_admin.py::TestUserList` | 4 |
| Admin: user detail + 404 | `test_admin.py::TestUserDetail` | 2 |
| Admin: plan update + audit log | `test_admin.py::TestPlanUpdate` | 4 |
| Admin: entitlement override merge | `test_admin.py::TestEntitlementOverrides` | 4 |
| Admin: admin flag grant/revoke/self-revoke | `test_admin.py::TestAdminFlag` | 5 |
| Admin: audit log list + filters + emails | `test_admin.py::TestAuditLog` | 5 |
| Frontend: error extraction | `extractError.test.ts` | 14 |
| Frontend: inbox store | `inboxStore.test.ts` | 5 |
| Frontend: SSE hook | `useSSE.test.ts` | 6 |
| Frontend: ProgressPanel rendering | `ProgressPanel.test.tsx` | 6 |
| Chip parsing ([CHIPS:] tag) | `test_chips_and_exports.py::TestChipParsing` | 4 |
| Generic chip filter (blocklist) | `test_chips_and_exports.py::TestGenericChipFilter` | 3 |
| Chip fallback sentinel | `test_chips_and_exports.py::TestChipFallback` | 2 |
| AI-powered chip generation | `test_chips_and_exports.py::TestChipAIFallback` | 2 |
| Safe filename slug utility | `test_chips_and_exports.py::TestSafeFilenameSlug` | 12 |
| Transcript service (PDF/TXT/MD) | `test_chips_and_exports.py::TestTranscriptService` | 7 |
| Field summary _has_value accuracy | `test_chips_and_exports.py::TestFieldSummaryHasValue` | 8 |
| Module completion: _question_range | `test_module_completion.py::TestQuestionRange` | 3 |
| Module completion: marker detection | `test_module_completion.py::TestIsModuleComplete` | 5 |
| Module completion: question counting | `test_module_completion.py::TestCountQuestionsAsked` | 4 |
| Module completion: prompt injection | `test_module_completion.py::TestPromptQuestionCountInjection` | 10 |
| Module completion: force-complete | `test_module_completion.py::TestForceCompleteIntegration` | 4 |
| Module completion: prompt preservation | `test_module_completion.py::TestPromptContentPreserved` | 5 |
| v2 SSE init greeting (stream + persist + done/chips + unified prompt) | `test_discovery_sse.py::TestInitGreetingV2` | 3 |
| v1 SSE init greeting (stream + done + differs from v2) | `test_discovery_sse.py::TestInitGreetingV1` | 2 |
| SSE init edge cases (404 missing, reject already-init) | `test_discovery_sse.py::TestInitEdgeCases` | 2 |
| v2 SSE message (field_update before done, summary, extraction-fail safe) | `test_discovery_sse.py::TestSendMessageV2` | 3 (+1 skip: PG-only upsert) |
| v1 SSE message (sheet_update before done, empty-extract path) | `test_discovery_sse.py::TestSendMessageV1` | 2 |
| SSE flow-version prompt branching (v2 unified vs v1 stage) | `test_discovery_sse.py::TestFlowVersionPromptBranching` | 3 |
| SSE message edge case (404 missing session) | `test_discovery_sse.py::TestSendMessageEdgeCases` | 1 |
| Notion: config gating + authorize URL | `test_notion_integration.py::TestConfig` | 4 |
| Notion: pure block rendering (v1 sheet / v2 modules / shared / truncation / coercion) | `test_notion_integration.py::TestRenderBlocks` | 6 |
| Notion: OAuth state mint/verify/tamper/scope | `test_notion_integration.py::TestOAuthState` | 3 |
| Notion: authorize route (503/200) | `test_notion_integration.py::TestAuthorizeRoute` | 2 |
| Notion: callback (success-stores-encrypted / error-param / bad-state / exchange-fail) | `test_notion_integration.py::TestCallbackRoute` | 4 |
| Notion: push (404/200/ownership-404/400) | `test_notion_integration.py::TestPushRoute` | 4 |
| Notion: list advertises `available` | `test_notion_integration.py::TestListIntegrations` | 1 |
| **Suite reality** | | **backend: 270 collected across 11 files — 265 pass · 1 skip (PG upsert) · 4 deselected (need live Anthropic) · frontend 37 across 5 files** _(verified 2026-05-31)_ |

**Known gaps (no test exists):**
- PostgreSQL ON CONFLICT upsert path — SQLite harness doesn't support `pg_insert` ON CONFLICT syntax. Production-verified-only until a PG-backed test environment is added. (Now also the sole remaining sub-gap inside the otherwise-covered SSE message route — see next bullet.)
- ~~SSE streaming routes (`/discovery/{id}/init` and `/message`)~~ — ✅ **covered as of 2026-05-30** by `test_discovery_sse.py` (16 pass + 1 skip). The AI boundary (`stream_response` / `generate_quick_chips` / `extract_module_fields` / `extract_sheet_fields`) is mocked; routing, flow-version branching, persistence, and SSE event assembly run for real. The only remaining sub-gap is the PG-only field-upsert (above).
- Frontend: DesignKit edit/save flow, Discovery flow_version branching, PathwayExecute v2 redirect, and the Notion components (`NotionConnectCard`, `NotionPushButton`) — verified only by `tsc` + manual/live smoke testing.

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

## Code Quality Snapshot (2026-05-27 — post module completion fix + audit)

- ✅ TypeScript: zero compilation errors
- ✅ Backend Python: **215/215 tests pass** across 8 files (41 service-layer v2 + 34 integration v2 + 31 module completion + 27 admin + 38 chips/slug/transcript/field-summary + 9 entitlements + 28 partner styles + 4 discovery resume + 3 misc). Syntax validated on all touched files.
- ✅ Frontend: 31/31 Vitest tests pass across 4 files
- ✅ Migration chain: linear 001→031, all reversible
- ✅ Auth: production-hardened with issuer + audience + azp enforcement; race-handling consolidated with INSERT ON CONFLICT
- ✅ SSE: always emits `done`; v2 emits `field_update` before done with default=str safety; frontend `useSSE` parses `field_update` via `onFieldUpdate`; chip pipeline is 4-stage (parse → pattern → AI → sentinel)
- ✅ Discovery v1: backward-compat fully preserved (v1 regression tests pass; scoped-session validation explicitly rejects v1 projects)
- ✅ Discovery v2 backend: all 6 phases shipped + audit-hardened + production bug-fixed. Scope validation, orphan safety, library isolation, field-summary value checking all regression-tested.
- ✅ Discovery v2 frontend: ProgressPanel, DesignKit (Edit/Refresh/Add Modules + mobile sticky CTA), scoped Discovery, scope-aware dep array, proceed gate on overall_percent, mobile overflow protection
- ✅ Phase 6 scoped sessions: scope validation against pathway, empty-scope normalization, v1 rejection, library/resume isolation — 16 regression tests
- ✅ Mobile: 19 pages use dynamic viewport + safe-area utilities; Discovery has `min-w-0`/`overflow-x-hidden`; DesignKit has responsive header + sticky CTA
- ✅ Error UX: ~40 silent failures surface via toast
- ✅ Export safety: `safe_filename_slug()` on all 7 export endpoints; PDF try/except
- ✅ Admin system: live + user-tested + 27 endpoint tests
- ✅ Realtime inbox: Redis pub/sub verified end-to-end in production
- ✅ Railway: all env vars set including REDIS_URL
- ✅ Doc versioning: convention live + Stop hook nags on missing CHANGELOG
- ⚠️ Webhook secrets: 3 exposed in chat — rotate when convenient
- ⚠️ One orphan user row in DB (no clerk_user_id) — leftover from debug
- ⚠️ JSONB `||` shallow merge known limitation for dict-typed fields (M1) — mitigated via extraction-prompt instruction to return whole dicts; not yet enforced server-side
- ❌ Discovery v2 upsert ON CONFLICT path not testable under SQLite — verified in production by manual smoke; PG-backed integration test environment would close this
