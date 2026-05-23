# Changelog

All notable changes to Ide/AI and its documentation. Format based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/). Doc versioning follows [DOC_VERSIONING.md](DOC_VERSIONING.md).

## [Unreleased]

### In progress — Unified Discovery overhaul (Phases 1-2 of 6 shipped)

The discovery → design kit flow is being restructured. Old `v1` projects keep the existing PathwayReview → Execute → per-module sessions path. New `v2` projects (default for all newly created projects) will use a unified Discovery that funnels toward filling fields across an up-front-assembled module pathway, then land directly on a complete Design Kit. See ROADMAP "Up Next" for the full 6-phase plan.

**Phase 1 (commit `fb840de`):**
- `projects.flow_version` column (migration 029) — `v2` default, existing rows backfilled to `v1`
- Field schemas on every module in `module_library.seed.json` — 40 modules, 154 total fields (52 required, 102 optional), 6 modules flagged `has_output`
- Up-front pathway assembly at project creation
- New helpers: `get_module_fields`, `get_pathway_field_summary`, `assemble_pathway_from_creation_inputs`

**Phase 2 (this commit):**
- `ai_service.build_unified_discovery_prompt(...)` — new system prompt builder that exposes ALL assembled modules + their field schemas + already-filled state, and instructs the AI to funnel toward the first unfilled REQUIRED field each turn. Layered with the existing partner-style fragments. Includes the standard CHIPS rules.
- `ai_service.extract_module_fields(messages, modules, current_fields)` — new extractor that returns a JSON dict keyed by `"module_id.field_key"`. Validates returned keys against the schema and drops anything not recognized. Handles markdown-fence-wrapped JSON.
- `discovery_service.get_filled_fields_for_project(...)` — loads current state of `module_responses.responses` grouped by module_id.
- `discovery_service.compute_field_summary(...)` — aggregates total/required/per-module completion counts for the progress meter payload.
- `discovery_service.apply_extracted_module_fields(...)` — writes extracted values into `module_responses` (creates rows on first touch, merges into existing rows otherwise) and returns `(updates_list, summary)` for the SSE event.
- **`/discovery/{id}/message` now branches on `project.flow_version`**:
  - v1 projects: unchanged — design-sheet prompt + sheet_update event
  - v2 projects: unified prompt + field_update event with the per-module summary
- New SSE event type: `field_update` carrying `{updates: [{module_id, field_key, value}], summary: {total_filled, total_fields, required_filled, required_total, overall_percent, per_module: [...]}}`
- Done event still always fires with chips fallback (Phase-pre fix from earlier today carried through).

Phase 3 (frontend Home category selector) is the next slice.

---

## [2026-05-23] — Discovery SSE Robustness

### Fixed
- **Assistant messages now persist independently from sheet extraction.** Previously, `/discovery/{id}/message` committed the assistant message AND sheet updates in the same transaction at the end of the stream. If the sheet extraction or its commit raised (JSONB serialization, concurrent write, etc.), the entire transaction rolled back — taking the assistant message with it. On resume, users saw only their own messages with the AI side missing. Fix: assistant message gets its own commit immediately after token streaming completes; sheet extraction is a separate transaction with its own rollback.
- **`done` event is now guaranteed to fire**, even when chip generation or JSON serialization fails. The final `yield` is wrapped in try/except with a hardcoded fallback sentinel. If `generate_quick_chips` raises, a 3-item generic chip list is used. This fixes the "chips appeared sometimes, randomly" symptom where the stream silently ended after the last token without emitting `sheet_update` or `done`.
- **Empty chip list from `generate_quick_chips`** now falls back to the 3-item default before being sent (was already happening for most code paths but a single-option `[CHIPS: x]` parse could slip through).
- **Same defensive wrapping applied to `/discovery/{id}/init`** (the greeting endpoint) — rollback on save failure, wrapped chip generation, wrapped final yield.

### Changed
- `CLAUDE.md` → 2.2.1 (PATCH bump — internal robustness, no documented-feature behavior change)

---

## [2026-05-23] — Realtime Inbox

### Added
- **Realtime inbox stream** at `GET /api/v1/inbox/stream` — Server-Sent Events, Redis pub/sub backed. Pushes `hello` (initial count) on connect, then `update` events on every mutation (added / promoted / deleted). Replaces the previous 60s polling.
- **`app/services/inbox_pubsub.py`** — module-level helpers (`publish_event`, `subscribe`, `is_available`) using `redis.asyncio` pub/sub on channel `inbox:user:{user_id}`. Lazy-initialized client. Graceful no-op when `REDIS_URL` is empty.
- **`REDIS_URL`** env var added to `config.py` (optional in dev — empty disables realtime and the stream endpoint returns 503)
- **Instrumented mutation paths** to publish events: `POST /inbox`, `POST /inbox/{id}/promote`, `DELETE /inbox/{id}`, `POST /webhooks/inbound-email`
- **Frontend stream client** in `inboxStore.ts` — `connectStream()` opens an authenticated fetch+reader to the SSE endpoint, parses SSE event blocks, updates count via `refresh()` (idempotent — sidesteps race with same-tab `adjust()` calls). Auto-reconnect with exponential backoff (1s → 30s cap). Server-said-no (503) latches `_giveUp` so the client doesn't hammer.

### Changed
- **Sidebar.tsx**: removed the 60s `setInterval` polling loop. `useEffect` now calls `connectStream()` on mount and `disconnectStream()` on unmount. Mount-time `refresh()` retained for an instant count before the stream's hello arrives.
- **`webhooks.py`**: inbound-email handler now refreshes the persisted item and publishes the event AFTER the DB commit (best-effort — doesn't extend the transaction window).
- **`pyproject.toml`**: added `redis>=5.0,<6.0` dependency.
- `CLAUDE.md` → 2.2.0: feature 19 (Idea Inbox) expanded with realtime architecture, env var docs, and the new `/inbox/stream` endpoint

### Deployment note
- **Railway**: add a Redis service to the project and set `REDIS_URL` on the backend service. The backend will start fine without it (stream returns 503, badge updates on page navigation only).

---

## [2026-05-23] — Roadmap Refresh

### Changed
- `ROADMAP.md` → 2.0.0: full restructure with frontmatter, "Recently Shipped" section listing today's commits, trimmed Short-Term Polish (toast + fetchPathway wraps moved to shipped), added "Up Next" queue (realtime inbox → Notion integration), refreshed Open Product Questions, added admin-metrics dashboard to Medium-Term

### Added
- Admin-system reference in Medium-Term Features (Billing & admin section) and Tech Debt (orphan user row cleanup)
- Stop-hook-shaped "Up Next" queue so the next session can pick up without re-derivation

---

## [2026-05-23] — Doc-Versioning Enforcement

### Added
- **CLAUDE.md "Documentation Discipline" section** with end-of-session checklist (6 steps), list of versioned docs + frontmatter format, bump rules, enforcement layers
- **Critical Rule #9** in CLAUDE.md binding every code-touching task to the discipline checklist
- **DOC_VERSIONING.md and CHANGELOG.md** added to Session Recovery's read-on-start list
- **Stop hook** at `.claude/hooks/check-doc-versioning.sh` that fires when a Claude Code session ends. Inspects the latest commit — if it touched `frontend/src/` or `backend/app/` files without touching CHANGELOG.md, prints a non-blocking reminder.
- **`.claude/settings.json`** registers the Stop hook under `hooks.Stop` (project-level config, committed to git)
- **`.claude/projects/.../memory/doc-versioning.md`** — project memory entry so the convention persists across all Claude conversations

### Changed
- `CLAUDE.md` → 2.1.0 (was 2.0.0): added Documentation Discipline section, Critical Rule #9, updated Session Recovery list
- `DOC_VERSIONING.md` → 1.1.0 (was 1.0.0): added Enforcement section describing the three layers (CLAUDE.md prominence, project memory, Stop hook)

---

## [2026-05-23] — Admin System, Error UX, Doc Versioning

### Added
- **Admin dashboard** at hidden `/admin` route (commit `3747eac`)
  - Backend: `/api/v1/admin/*` router with `require_admin` dep
  - Endpoints: list/detail users (paginated, searchable), change plan, set entitlement overrides, grant admin, audit log
  - Frontend: lazy-loaded Admin page with Users + Audit Log tabs, drawer with plan toggle / override editor / admin grant
  - `users.is_admin` (bool) and `users.entitlement_overrides` (JSONB) columns
  - `admin_audit_log` table (append-only record of every admin action)
  - `adminStore` (Zustand) for user list, detail, audit list with optimistic mutations
  - Sidebar shows "Admin" link conditional on `user.is_admin`
- **DB migrations 027 + 028**
- **Doc versioning system**: `DOC_VERSIONING.md` convention + this `CHANGELOG.md`
- **Frontmatter** (Version + Last updated + CHANGELOG link) on all versioned docs

### Changed
- `entitlement_service.get_limits()` now merges `users.entitlement_overrides` over plan defaults — any key present in overrides wins; `null` means unlimited
- `UserProfile` schema exposes `is_admin` field for frontend gating
- `AuthUser` interface in `authStore` includes `is_admin: boolean`

### Security
- **Railway env vars activated**: `CORS_ORIGINS`, `CLERK_ISSUER`, `CLERK_AUTHORIZED_PARTIES` — production JWT hardening now enforces tokens originate from this Clerk instance and authorized origins
- Self-revoke of admin status blocked at the API layer (prevents lockout)

### Fixed
- **~40 silent failure sites converted to user-visible toasts** across 18 components (commit `28ead2d`)
  - Discovery, Blocks, Library, Pipeline, Exports, PromptKit, MarketAnalysis, SprintPlanner, PitchMode, ShareDialog, TranscriptExportMenu, TemplateGrid, ModuleSession, PathwayExecute
  - Removed inline error banners in Profile, CommentSection, StarRating, billing/UpgradeModal in favor of toasts
- Wrap unhandled `fetchPathway()` rejections in `ModuleSession.tsx:73` and `PathwayExecute.tsx:43` (404s stay silent; other failures toast)
- Added `toast.success()` on milestones: import, snapshot save/restore, share link create/revoke, comment post

---

## [2026-05-22] — Mobile Viewport + Audit Cleanup

### Added
- `.h-dvh` and `.pb-mobile-nav` Tailwind utilities for iOS-safe viewport sizing (commit `fb1f1b8`)
- Save Place button in Discovery TopBar (commit `9c5ef1c`)
- VoiceMicButton wired into Discovery input row (commit `5db42eb`)
- Drag-and-drop Blocks board via `@dnd-kit/core` (commit `5db42eb`)
- AI partner picker per inbox item (commit `253b30a`)
- PitchMode React Flow user-flow diagram from MVP blocks (commit `253b30a`)
- `inboxStore` (Zustand) for sidebar unread badge with 60s polling
- `react-hot-toast` globally wired in `App.tsx`

### Changed
- SSE event order in Discovery: `sheet_update` now fires BEFORE `done` (so clients that close on done sentinel still receive sheet updates)
- `auth.py` race handling consolidated with `INSERT ... ON CONFLICT (clerk_user_id) DO NOTHING`
- `ui/UpgradeModal.tsx` renamed to `ui/EntitlementLimitModal.tsx` to disambiguate from the plan picker

### Fixed
- Transcript copy now includes AI messages (Axios `responseType: 'text'` for markdown response)
- PathwayReview Proceed-button errors now surface via toast + inline banner instead of infinite spinner
- Mobile viewport conformance across 19 pages — `h-screen` (100vh) replaced with `.h-dvh`, `pb-14` replaced with `.pb-mobile-nav`
- iPhone home indicator no longer overlaps bottom nav (safe-area-inset applied)
- 8 audit findings closed with 2-agent verification per fix (commit `253b30a`)

---

## [2026-05-21] — Post-Update Audit

### Added
- Backend test infrastructure (37 tests passing)
- Centralized entitlement guards on all creation paths (free=3 projects / basic=25 / pro=unlimited)
- Private share viewer JWT tokens (6-hour, HS256)
- Svix webhook verification + Resend inbound email idempotency (migration 025)

### Changed
- Discovery autosave rewritten with ref-based pattern (no message-array overwrite)
- Library resume routing now gates on Discovery stage before routing past Discovery
- Pathway completion sync after module complete/skip

### Fixed
- Empty-session recovery now prefers non-empty session via `jsonb_array_length`
- Frontend lint cleanup — zero errors

---

## [2026-05-22] _(earlier)_ — Auth Race + Discovery Polish

### Fixed
- Duplicate user crash (auth.py race handling + migration 026 dedup)
- Quick chips always appear (event_stream try/except wrapping)
- Design sheet update fix (`extract_sheet_fields` JSON parsing robustness)
- AI partner anti-repetition (CONVERSATION RULES block with message_count)

---

## Format note

Doc-only changes (e.g. bumping CLAUDE.md version after a content tweak) belong in the same entry as the code change they describe. Standalone doc-only bumps (typo fixes, version-table refreshes) are batched into a small "Doc cleanup" entry at the next release date.
