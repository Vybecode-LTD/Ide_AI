# Changelog

All notable changes to Ide/AI and its documentation. Format based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/). Doc versioning follows [DOC_VERSIONING.md](DOC_VERSIONING.md).

## [Unreleased]

### Phase 4 HTTP-level integration tests + H1 prod-bug fix

After the audit closure, added FastAPI TestClient-based integration tests covering the HTTP routes the service-layer tests in `test_discovery_v2.py` couldn't reach. The new suite immediately caught a real production bug in the H1 fix.

### Fixed
- **`projects.py` greenlet-during-serialization bug.** The H1 downgrade (`project.flow_version = "v1"; await db.flush()`) was implicitly expiring `updated_at` (server_default/onupdate column). FastAPI's response-serialization then tried to lazy-load it outside the greenlet context, raising `MissingGreenlet`. Fix: `await db.refresh(project)` after the downgrade so all server-default columns are populated before serialization. Every H1-downgraded project would have hit this in production (any POST /projects without primary_category, or with a failing assembly). Caught by `test_downgrades_to_v1_when_no_primary_category` in the new integration suite.

### Added
- **`backend/tests/test_discovery_v2_integration.py`** — 15 tests using FastAPI TestClient with dependency overrides for `get_db` + `get_current_user`. Covers:
  - **TestCreateProjectH1** (5 tests): v2-with-pathway happy path, H1 downgrade on no-category, H1 downgrade on empty assembly (monkeypatched), H1 downgrade on assembly exception (monkeypatched), Phase-2-hotfix invariant that `module_pathways.modules` is `list[str]`.
  - **TestFieldSummaryEndpoint** (4 tests): 200 + correct shape for v2, 409 for v1, 404 for nonexistent session, 404 for cross-user session (security check).
  - **TestTemplateFlowVersion** (1 test): Phase 3 hotfix invariant that template-created projects are `flow_version='v1'`.
  - **TestLibraryResumeRouting** (2 tests): exhaustive matrix proving v2 always routes to `/discovery`, plus v1 routing unchanged across all 5 legacy states.
  - **TestDiscoveryStartV2** (2 tests): session creation with partner-style propagation, cross-user 404 isolation.
  - **TestProjectReadShape** (1 test): asserts every field the Phase 4 frontend `Project` type expects is present in the response.

### Coverage summary
- **Backend tests: 91 total, all passing** (41 existing + 35 unit + 15 integration).
- Phase 1-4 + audit closure now has HTTP-level regression coverage for: H1 (4 cases), M6 endpoint (4 cases), Phase 3 hotfix (template v1 flag), `_compute_resume_path` (exhaustive matrix), discovery start ownership check, ProjectRead shape, pathway-shape invariant. PostgreSQL ON CONFLICT upsert is still out of scope (SQLite harness). SSE streaming endpoints are not exercised — that would require mocking the AsyncAnthropic streaming client.

### Changed
- **CLAUDE.md → 2.7.1** (PATCH — real bug fix in `projects.py` + new test file, no documented-feature change).

### Phase 4 audit closure (previous commit)

End-of-Phase-4 internal audit identified 2 HIGH, 8 MEDIUM, 5 LOW findings across the v2 code paths. All actionable items resolved in a single sweep with regression testing between each phase. 76/76 backend tests now pass (35 new v2 tests + 41 existing), TypeScript build clean.

### Fixed
- **H1 — v2 project stranded when up-front assembly skipped.** [projects.py](backend/app/routers/projects.py) now downgrades `flow_version` to `'v1'` when no pathway row is created (no `primary_category`, empty assembly, or assembly exception). Previously these orphan v2 projects rendered ProgressPanel forever empty + no Proceed button.
- **H2 — `PathwayExecute.tsx` missing v2 redirect.** Defense-in-depth gap closed. v2 users who deep-link to `/pathway-execute/{pid}` now bounce back to Discovery, matching the existing PathwayReview behavior. Prevents the legacy per-module session from clobbering v2-populated `module_responses`.
- **M8 — Proceed button never appeared for all-optional pathways.** Gate changed from `required_total > 0` to `total_fields > 0` in [Discovery.tsx](frontend/src/pages/Discovery.tsx). Warning chip still only shows when `required_total > 0` AND `required_filled / required_total < 80%`.
- **New defensive check in `apply_extracted_module_fields`** — unknown field keys (compound keys within valid modules but not in the schema) are now logged + rejected instead of silently coerced to text and persisted. Caught by the new test suite.

### Added
- **M6 — `GET /api/v1/discovery/{session_id}/field-summary` endpoint.** Returns the current `compute_field_summary` payload for a v2 session. Frontend `Discovery.tsx` now hydrates the ProgressPanel from this endpoint on mount, closing the resume-mid-session blank-state gap. Returns 409 for v1 projects so the client knows to render the legacy panel.
- **M3 — `build_unified_greeting_prompt`** in `ai_service.py`. v2 projects get a greeting that names the assembled module set + steers toward the first required field's extraction hint. Init handler in `discovery.py` branches on `flow_version`. v1 keeps the legacy `build_greeting_prompt`.
- **M7 — `_coerce_field_value` drop logging** with module/field/declared-type/raw-value context. Surfaces silent extraction drops in Railway logs without affecting UX.
- **M1 — extraction prompt instructs dict fields to return whole object** (existing keys merged with new updates) so the JSONB shallow merge doesn't lose nested keys.
- **`load_decorated_pathway_modules` service helper** in `discovery_service.py` — extracted from the inline decoration logic in the message handler so the new field-summary endpoint can reuse it. Tolerates both list[str] and legacy list[dict] shapes.
- **L5 — `_reset_module_library()` test hook** in `modular_pathway_service.py`. Lets tests force a re-read of the seed file or inject a mock library.
- **I4 — new test file `backend/tests/test_discovery_v2.py`** with 35 tests covering: `_coerce_field_value` (12 cases), `_reset_module_library` (2), `compute_field_summary` (4 DB-backed), `load_decorated_pathway_modules` (4 DB-backed), `apply_extracted_module_fields` (2 — validation logic, not the PG-only upsert), `build_unified_discovery_prompt` (3), `build_unified_greeting_prompt` (3).

### Changed
- **L1 — ProgressPanel "just filled" highlight fades after 8s.** `recentUpdates` state auto-clears via `setTimeout` so the accent doesn't linger between AI turns.
- **L2 / M5 — ProgressPanel expanded set capped at 3 modules** with FIFO eviction. Applies to both auto-expand (on field_update) and manual user clicks. Prevents scroll clutter on long sessions with many module updates.
- **M2 / L3 — Stage UI hidden for v2.** `Discovery.tsx` no longer renders TopBar subtitle (`Stage: greeting`), left StagesStepper, or mobile stage indicator for v2 projects. v2 has no meaningful stage progression; the ProgressPanel carries the equivalent signal.
- **M4 — `loadSheet()` skipped for v2.** Bootstrap effect in `Discovery.tsx` consolidated: project fetched first, `flow_version` known before session start, design-sheet load only runs for v1. Removes the wasted 404 round-trip on v2 session start.
- **CLAUDE.md → 2.7.0** (MINOR — new endpoint + new helper + new test file, all backwards-compatible).

### In progress — Unified Discovery overhaul (Phases 1-4 of 6 shipped)

The discovery → design kit flow is being restructured. Old `v1` projects keep the existing PathwayReview → Execute → per-module sessions path. New `v2` projects (default for all newly created projects) will use a unified Discovery that funnels toward filling fields across an up-front-assembled module pathway, then land directly on a complete Design Kit. See ROADMAP "Up Next" for the full 6-phase plan.

**Phase 4 (this commit) — frontend ProgressPanel + v2-aware Proceed gate + overlay a11y:**
- **`components/discovery/ProgressPanel.tsx`** (new) — module-aware progress meter that replaces `DesignSheetPanel` on the right side of Discovery for v2 projects. Renders overall % header with progressbar role, expandable per-module breakdown showing filled / required-left / optional-left counts, and an accent highlight on fields just-filled by the latest extraction batch. Auto-expands whichever module the AI most recently extracted into.
- **`hooks/useSSE.ts`** — new `onFieldUpdate` callback + exported `FieldUpdate`, `FieldSummary`, `FieldUpdatePayload` types. Parses the `field_update` SSE event emitted by the Phase 2 backend (previously silently dropped). `onSheetUpdate` (v1) and `onFieldUpdate` (v2) coexist; only one fires per AI turn depending on `project.flow_version`.
- **`pages/Discovery.tsx`** branches on `flowVersion`:
  - Fetches `flow_version` from `GET /projects/{id}` on mount and stores it. Falls back to `'v1'` if the project fetch errors so the legacy sheet panel still renders.
  - Right side renders `<ProgressPanel>` for v2, `<DesignSheetPanel>` for v1.
  - Mobile toggle button label switches between "Progress" and "Sheet"; badge shows `overall_percent` (v2) or `confidence_score` (v1).
  - Proceed button gate replaced. v1 unchanged (`sheet.confidence_score >= 70` → `/pathway-review/{id}`). v2 always available once `fieldSummary.required_total > 0`, routes to `/exports/{id}` as the interim Design Kit destination (the Phase 5 `/design-kit/{id}` page swaps the destination in). Warning chip with the live `required_filled / required_total` percentage when below 80%.
- **`pages/Home.tsx` module-preview overlay a11y + mobile (Phase-3-deferred audit items):**
  - Extracted to new `ModulePreviewOverlay` subcomponent with `role="alertdialog"`, `aria-labelledby` on heading, `aria-describedby` on subtitle.
  - Dialog focused on mount; `Escape` key skips the 2.2s wait and navigates immediately. Visible "Skip Esc" hint in the footer.
  - Mobile overflow fix: dialog `max-h-[88vh]`, grid `max-h-[40vh]` on small screens (was `max-h-60` / 240px, which overflowed at <360px viewport).
  - Destination URL captured on the overlay state so the Esc handler can navigate without recomputing it.
- **`types/project.ts`** — added `flow_version: 'v1' | 'v2'` plus `primary_category`, `secondary_category`, `pathway_locked` (all returned by backend `ProjectRead` but missing from the frontend type until now).

Known Phase-4 limitation (intentional, scoped to Phase 5): on resume, the ProgressPanel shows its empty state until the user's next message. The `field_update` event fires after AI replies, not on session-resume. A dedicated `GET /discovery/{id}/field-summary` endpoint to seed the panel on mount is a Phase 5 follow-up — once `/design-kit/{id}` exists, it'll load the summary directly and resume-on-Discovery becomes less common.

- CLAUDE.md → 2.6.0 (MINOR — new user-visible feature: ProgressPanel + v2 Proceed gate + a11y improvements)

**Phase 1 (commit `fb840de`):**
- `projects.flow_version` column (migration 029) — `v2` default, existing rows backfilled to `v1`
- Field schemas on every module in `module_library.seed.json` — 40 modules, 154 total fields (52 required, 102 optional), 6 modules flagged `has_output`
- Up-front pathway assembly at project creation
- New helpers: `get_module_fields`, `get_pathway_field_summary`, `assemble_pathway_from_creation_inputs`

**Phase 3 hotfix (this commit, post 2-agent audit):**
- **`Home.tsx` setTimeout leak fixed** — preview-navigate timer is now stored in a `useRef` and cleared in an unmount effect. Previously the orphan timer could fire after the component unmounted, yanking a user away from wherever they manually navigated to during the 2.2s preview window.
- **`Home.tsx` billing-URL category preservation** — the billing-success cleanup effect now strips only `?billing=success` and preserves all other query params (notably `category`). Previously a user landing on `/home?category=software&billing=success` lost their category selection mid-flow.
- **`templates.py` flow_version='v1'** — template-created projects now explicitly set `flow_version='v1'` (was defaulting to `'v2'` from the column default). Template projects don't run up-front pathway assembly, so being marked v2 would break Library resume routing and PathwayReview redirects. Phase 5 may revisit once `/design-kit` can render template-seeded fields.
- **`library.py:_compute_resume_path` flow_version branch** — v2 projects now always resume to `/discovery/{pid}` (the unified Discovery is their only surface until Phase 5's `/design-kit` ships). v1 routing untouched.
- **`PathwayReview.tsx` v2 redirect** — fetches the project on mount; if `flow_version === 'v2'`, immediately redirects to `/discovery/{projectId}` so v2 users who deep-link or get bounced here don't fall into the legacy review/lock flow which would clobber their up-front-assembled pathway.
- CLAUDE.md → 2.5.1 (PATCH — pure bug fixes, no documented-feature change)

Audit findings deferred to Phase 4 (not blockers for handoff):
- Discovery "Proceed to Design Kit" button still requires `sheet.confidence_score >= 70` (effectively unreachable for v2). Phase 4 ProgressPanel replaces this trigger with a field-completion check.
- DesignSheetPanel on the right side of Discovery still renders for v2 (empty/blank state). Phase 4 swaps it for ProgressPanel.
- Module-preview overlay a11y (`role="status"` vs `role="alertdialog"`) and mobile overflow on tiny viewports.

**Phase 3 (commit `94102cb`) — frontend Home reorder + post-create module preview:**
- Moved `TemplateGrid` directly below the partner-style picker (was below the Submit button) per the v2 UX spec: "partner style with templates below it and optional advanced configuration".
- New `showPreviewAndNavigate(projectId)` flow on the Submit handler: after a v2 project is created, fetch `/projects/{id}/pathway`, then show a glassmorphism overlay listing every module the AI will fill during Discovery, then auto-route to `/discovery/{id}` after 2.2 seconds.
- Overlay is animated (AnimatePresence) with per-module stagger. Falls through to immediate navigation when the pathway endpoint 404s (template projects, v1 projects, or assembly skipped at creation).
- Tolerates both list-of-strings AND list-of-dicts shape from `/projects/{id}/pathway` (legacy data) so the overlay renders cleanly whether migration 030 has run or not.
- Frontend now respects `data.flow_version === 'v2'` returned from POST /projects to decide between the overlay path and the legacy immediate-nav path.
- CLAUDE.md → 2.5.0 (MINOR — new user-visible UX flow).

**Phase 2 hotfix (commit `23f5e7d`):**
- **Migration 030** — three forward-only data fixes:
  1. Backfill `module_pathways.modules` from list[dict] → list[str] for any rows already created on the broken Phase-1 shape
  2. Dedup `module_responses` by (project_id, module_id) keeping the newest row per pair
  3. Add `UNIQUE(project_id, module_id)` on `module_responses` so the race-safe ON CONFLICT upsert can apply field updates without duplicate-row pile-ups
- **`projects.py`** now stores module-id strings only on `module_pathways.modules` (matches `PathwayRead.modules: list[str]` and `modules.py`/PathwayExecute consumers). Empty assembly results no longer create an orphan pathway row.
- **`discovery.py`** now decorates `mp.modules` (strings) into full module entries (with `label`, `description`, `group`, `fields`, `has_output`) at read time by looking up the library definition. Tolerates legacy list[dict] shape too in case migration 030 hasn't run for a given DB.
- **`discovery_service.apply_extracted_module_fields`** rewritten to use PostgreSQL `INSERT ... ON CONFLICT (project_id, module_id) DO UPDATE` with JSONB `||` merge. Concurrent calls from the same project (multi-tab, retry) no longer race.
- **Type coercion** via new `_coerce_field_value(value, field_type)` helper — if the AI returns a string for a list-typed field, it's wrapped; a dict for a list field is values-extracted; a scalar for a dict field is rejected (returns None). Defends against schema-shape drift.
- **SSE serialization safety**: `json.dumps(..., default=str)` on all event payloads in discovery.py — guards against datetime / UUID / Decimal values sneaking in from JSONB columns.
- **CLAUDE.md** → 2.4.1 (PATCH bump — internal robustness, no documented-feature change)

**Phase 2 (commit `8cfc66a`):**
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

Phase 5 (Design Kit page at `/design-kit/{id}` with per-module Edit + Refresh affordances) is the next slice. Phase 6 (Additional Discovery for newly-added modules) closes the v2 frontend overhaul.

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
