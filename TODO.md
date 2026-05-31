# Ide/AI — TODO

> **Version:** 3.13.0 · **Last updated:** 2026-05-31 · See [CHANGELOG.md](CHANGELOG.md)
>
> Concrete actionable items. See [`ROADMAP.md`](ROADMAP.md) for strategic direction, [`CONTEXT_HANDOFF.md`](CONTEXT_HANDOFF.md) for current-session state + the **Regression Test Matrix** (which code path is protected by which test file), and [`MEMORY.md`](MEMORY.md) for conventions + recent-session signature.

---

## 🔴 P0 — none open (cleared 2026-05-30)

- [x] **Push all pending commits** — ✅ DONE 2026-05-30. 8 commits pushed; Railway deployed both services green.
- [x] **Export `og-image.png`** (1200×630) — ✅ DONE; present in `frontend/public/`.
- [x] **Production smoke test** — ✅ DONE 2026-05-30. Sign-in, admin dashboard, and profile all verified live (after resolving the two-part CSP incident — see Recently Done + [`CONTEXT_HANDOFF.md`](CONTEXT_HANDOFF.md)).
- [x] **Rotate 3 webhook signing secrets** — ✅ DONE 2026-05-30. User rotated the webhook secrets **and** the API keys (Clerk/Stripe/Resend), updated Railway env, sign-in verified.

> Remaining open items are non-blocking — see the 🛡 Security hygiene and 🟡 High Priority sections below (SAST-H1 rate limiting, DEP-H1 js-cookie CVE, stale `AGENTS.md`). _(Discovery v2 SSE streaming tests — ✅ done 2026-05-30.)_

---

## 🟢 Tutorial + Blog (SHIPPED 2026-05-31)

Both features are built, fully verified (backend 293→288 pass, frontend 60/60, `tsc`/ESLint/`npm run build` all green), and **shipped** — merged `--no-ff` (`4a15472`) + pushed; Railway auto-deployed + ran migration 033. See [CONTEXT_HANDOFF.md](CONTEXT_HANDOFF.md) "Current Session".

- [x] **Commit + deploy** — ✅ DONE 2026-05-31. Merged `--no-ff` (`4a15472`) + pushed (`7a70335..4a15472`); Railway auto-deployed both services; migration 033 ran via the pre-deploy hook.
- [ ] **Bootstrap an admin** before the Blog CMS is usable — `UPDATE users SET is_admin=TRUE WHERE id='<id from /auth/me>'`. Then Admin → "Blog" tab + `/blog/admin/*` work. (Public blog reads need no auth.)
- [ ] **Manually test live** (Rule #8): tour auto-launch on a fresh sign-in + "?" replay + Settings "Replay Walkthrough"; publish a post from the admin CMS → renders at `/blog/{slug}` with correct title/meta.
- [ ] **Decide tour auto-launch scope** — currently fires once for *everyone* lacking the `ideai-walkthrough` localStorage key (incl. existing users, one time). Make it new-signups-only? Needs a "new user" signal (account age / backend flag).
- [ ] **Blog SEO fast-follow (optional):** build-time prerender of published posts + dynamic `sitemap.xml` entries (Known Issue #6). Couples the frontend build to backend availability — design accordingly. Until then, blog pages are client-rendered with full Helmet meta + JSON-LD (Googlebot renders JS).
- [ ] **"?" position polish (optional):** sits `top-3 right-3`; on mobile pages with a TopBar the Clerk avatar shares that corner — nudge if it crowds.

---

## 🚦 Phase 5 — Design Kit page at /design-kit/{projectId} (next active work)

Phase 4 + audit closure + integration tests are all shipped. Phase 5 builds the final v2 destination — a per-project Design Kit view that replaces `/exports/{id}` as the Proceed target.

**All items completed in order.** Vitest scaffold landed first (31 tests), then Design Kit + Edit + PATCH, then Proceed swap + Library routing, then Refresh + Add Modules. Every endpoint shipped with matching integration tests.

- [x] **1. `pages/DesignKit.tsx` + route** at `/design-kit/:projectId`. ✅ DONE in `f6682cd`. ModuleCard components, FieldEditor (type-aware), FieldDisplay, grouped by module group, overall progress bar, Export button.
- [x] **2. Per-module Edit affordance** — ✅ DONE in `f6682cd`. Inline form per module with field-type-aware inputs (text/longtext/list-as-chips/dict-as-key-value-rows).
- [x] **3. Backend: `PATCH /api/v1/modules/{project_id}/{module_id}/responses`** — ✅ DONE in `f6682cd`. Validates keys against schema, reuses `_coerce_field_value` + unknown-key rejection. 5 integration tests.
- [x] **4. Refresh affordance for `has_output` modules** — ✅ DONE. `POST /api/v1/modules/{project_id}/{module_id}/refresh-output` generates formatted output from field values via AI. Returns 400 for non-has_output modules. Frontend: "Generate Output" / "Regenerate" button on DesignKit module cards. Output stored in `responses.__generated_output`. 3 integration tests.
- [x] **5. "Add Modules" button** — ✅ DONE. Category-filtered picker modal in DesignKit. Backend: `POST /api/v1/projects/{project_id}/pathway/modules` appends, validates IDs, deduplicates. 3 integration tests.
- [x] **6. Swap the v2 Proceed destination** — ✅ DONE in `f6682cd`. Discovery.tsx v2 Proceed now routes to `/design-kit/${projectId}`.
- [x] **7. Update Library resume routing** — ✅ DONE in `f6682cd`. v2 completed sessions/pathways resume to `/design-kit/{pid}`. Split integration test into in-progress vs completed cases.

---

## 🧭 Phase 6 — Additional Discovery for newly-added modules ✅ DONE

- [x] **Mini-Discovery flow** — scoped sessions via `scope_module_ids` JSONB on `discovery_sessions` (migration 031). `POST /discovery/start` accepts `scope_module_ids`; init/message/field-summary filter to scope. 4 integration tests.
- [x] **"Continue Discovery" button** — DesignKit header shows "Continue Discovery (N)" when modules have unfilled required fields. Navigates to `/discovery/:projectId?scope=mod1,mod2,...`.
- [x] **Session isolation** — scoped sessions never hijack main-flow resume. `get_latest_active_session_for_project` excludes scoped sessions via `scope_module_ids IS NULL` filter.
- [x] **Frontend scoped mode** — Discovery.tsx reads `?scope=` param, passes to start endpoint, TopBar shows "Continue Discovery" + scope count, Proceed reads "Back to Design Kit".
- [x] **Phase 6 audit hardening** — 6-agent audit found 6 HIGH + 8 MEDIUM + 8 LOW findings. Fixed: library subquery scope leak, orphan cleanup scope leak, scope ID validation against pathway, empty-scope normalization, frontend dep array, DesignKit unfilled-check logic, migration docstring, model type annotation. 16 regression tests added (4 audit + 6 integration + 6 service-layer). 123/123 backend, 31/31 frontend.

---

## 🛡 Security hygiene (recommended)

- [x] ~~**Rotate 3 webhook signing secrets**~~ — **DONE 2026-05-30** (webhook signing secrets + API keys for Clerk/Stripe/Resend rotated, Railway env updated, sign-in verified). _(Duplicate of the cleared P0 item above.)_
- [ ] **SAST-H1: Rate limiting on sharing endpoints** — `/sharing/public/{token}/comments` and `/sharing/public/{token}/ratings` are anonymous and have no rate limiting. Install `slowapi` (or `fastapi-limiter`), add per-IP limits (e.g. 10 req/min per token). Also consider rate-limiting the webhook endpoints.
- [x] ~~**SAST-H2: OpenAPI docs in production**~~ — **DONE 2026-05-28**. `docs_url`, `redoc_url`, `openapi_url` now `None` when `ENVIRONMENT=production`.
- [x] ~~**SAST-M1: Stripe error leak**~~ — **DONE 2026-05-28**. Generic message returned to client, raw error logged.
- [x] ~~**SAST-M2: Content-Security-Policy**~~ — **DONE 2026-05-28**. CSP header added to Caddyfile.
- [ ] **DEP-H1: js-cookie CVE** — transitive from `@clerk/shared` v3.0.5. Check if upgrading `@clerk/clerk-react` resolves it. If not, document as upstream and monitor.

---

## 🟡 HIGH PRIORITY

### Remaining toast migrations (light)
Most error sites are now toast-surfaced (commit `28ead2d`). What's left:

- [x] ~~**`Home.tsx`** — `createError` state → `toast.error(extractError(...))`~~ — **DONE**.
- [x] ~~**`SprintPlanner.tsx`** — removed `errorMessage` state, unified on `toast.error()`~~ — **DONE**.
- [ ] **`pathwayStore.ts`** and **`ErrorBoundary.tsx`** intentionally left as `console.error` — both are framework-level, not user-facing. No change needed.

### Test coverage

> Before adding tests, check the **Regression Test Matrix** in [`CONTEXT_HANDOFF.md`](CONTEXT_HANDOFF.md) — it lists every code path currently covered (**backend: 270 collected across 11 files — 265 pass · 1 skip · 4 deselected + 37 frontend across 5 files**) and the explicit gaps. Avoid duplicating coverage.

- [x] ~~**Frontend tests** — Vitest setup + first tests~~ — **DONE**. 31 tests across 4 files.
- [x] ~~**Backend admin endpoint tests**~~ — **DONE**. 27 tests in `test_admin.py`.
- [x] ~~**Discovery v2 endpoint integration tests**~~ — **DONE**. 34 tests in `test_discovery_v2_integration.py`.
- [x] ~~**Chip relevance + export + field summary tests**~~ — **DONE 2026-05-25**. 38 tests in `test_chips_and_exports.py`: chip parsing (4), generic filter (3), fallback sentinel (2), AI fallback (2), safe slug (12), transcript PDF/TXT/MD (7), field summary _has_value (8).
- [x] ~~**Discovery v2 SSE streaming tests**~~ — **DONE 2026-05-30**. `backend/tests/test_discovery_sse.py` (16 pass + 1 documented skip) covers `/discovery/{id}/init` + `/message`: token streaming, greeting persistence, `field_update` (v2) vs `sheet_update` (v1) emitted before `done`, v2-vs-v1 prompt branching, and extraction-failure-still-emits-done. Mocks the AI boundary only (`stream_response` / `generate_quick_chips` / `extract_module_fields` / `extract_sheet_fields`); everything else runs for real. The one skip is the PG-only `||` upsert (needs a Postgres harness).
- [ ] **Discovery v2 upsert tests** — `apply_extracted_module_fields` ON CONFLICT path requires PostgreSQL — out-of-scope for the SQLite test harness. Either add a PG-backed integration test environment (testcontainers-python) or document as production-verified-only.

### DB cleanup
- [ ] **Orphan user row** — one row exists with `is_admin = TRUE` but no `clerk_user_id`, from the dedupe debug. Safe to leave or `DELETE FROM users WHERE id = '<orphan_id>'`. Verify no FKs reference it first:
  ```sql
  SELECT id, email, is_admin, clerk_user_id FROM users WHERE email ILIKE '%your_email%';
  -- Then check FK tables before delete (projects.user_id, idea_inbox.user_id, etc.)
  ```

---

## 🟢 NICE TO HAVE (Backlog)

### UX
- [ ] **Cross-tab inbox badge sync** — add `storage` event listener in `inboxStore.ts` so tab A adds an idea and tab B's badge updates instantly.
- [ ] **Print mode polish on PitchMode** — already added CSS overrides; do a real print preview to confirm.
- [ ] **Empty-state illustrations** on Blocks/Pipeline/PromptKit when no data exists yet.
- [ ] **Keyboard shortcuts** — Cmd+K command palette for navigating between project sections.
- [ ] **Sidebar inbox badge animation** — pulse on count increase.

### Code organization
- [ ] **Hoist `_partnerCache`** to `frontend/src/lib/partnerCache.ts`. Currently duplicated in `Home.tsx` and `Inbox.tsx`.
- [ ] **`inbox.py` lazy import** — `validate_partner_style` is imported inside `promote_to_project`. Move to module-level (no circular import risk).
- [ ] **Remove unused `setError` import** from any file where toast replaced it.

### Documentation
- [ ] **Add `frontend/src/components/voice/README.md`** — document the Web Speech API integration and browser support matrix.
- [ ] **Add MIGRATION_GUIDE.md** if any breaking schema changes happen (currently none planned).
- [x] ~~**Update `DEPLOYMENT_RAILWAY.md`**~~ — **DONE 2026-05-27**. Rewritten for actual 2-service topology (no reverse proxy).

---

## 🧪 Testing Debt

### Backend (extend existing test suite)
- [ ] Test `_link_existing_email_user` race scenario (webhook-first user creation)
- [ ] Test `_idempotent_create_user` ON CONFLICT path (race with another request)
- [ ] Test `validate_partner_style` rejection cases in inbox promotion
- [ ] Test `/inbox/count` returns correct unpromoted count
- [ ] Test SSE event ordering: `sheet_update` fires before `done` when extraction succeeds

### Frontend (31 tests landed in `01af5a6`)
- [x] ~~Vitest setup + first test (extractError function — pure, no UI)~~ — 14 tests
- [x] ~~`inboxStore.adjust(-1)` clamps at 0 (no negative counts)~~ — 5 tests
- [x] ~~`useSSE` hook safety-net fires `onDone` when stream ends without done event~~ — 6 tests
- [ ] `PathwayReview.init()` 404 path doesn't show error toast
- [ ] `DesignKit.tsx` edit/save flow + field-type rendering

### Manual smoke (post-deploy)
- [ ] iOS Safari: Discovery viewport doesn't cut off above keyboard
- [ ] iPhone home indicator: nav has proper safe-area padding
- [ ] Android Chrome: TopBar chips horizontally scroll on narrow screens
- [ ] Voice mic: works in Chrome desktop + Chrome Android, gracefully hidden on Firefox
- [ ] Drag-and-drop Blocks: works with mouse, touch, and keyboard (tab + arrow keys)
- [ ] react-hot-toast positioning doesn't overlap UpgradeModal/EntitlementLimitModal

---

## 🛡️ Security Hardening (Optional)

- [ ] **Rate limit `POST /pathways/detect`** — currently unauthenticated could spam Anthropic calls (though Clerk verification gates it... double-check this).
- [ ] **Audit `Sharing` public endpoints** — comments/ratings accept arbitrary text. Add length limits + basic profanity filter or moderation queue.
- [ ] **Audit `Inbox` webhook endpoint** — currently has 256KB payload cap. Consider also rate-limiting per-user.
- [ ] **Verify Clerk JWT clock skew tolerance** — `pyjwt` default is 0; some clock drift in production could cause spurious 401s. Set `leeway=30` in `verify_clerk_token`.
- [ ] **Audit Stripe webhook idempotency** — verify duplicate webhook events don't double-charge or double-create.

---

## 📦 Dependency Updates

Run periodically:
```bash
cd frontend && npm.cmd outdated
cd backend && pip list --outdated
```

Last audited: 2026-05-23
- Frontend: 2 high-severity vulnerabilities (pre-existing, in transitive deps not directly used)
- Backend: TBD — no recent audit

---

## 🗑️ Cleanup

- [ ] Delete `AGENTS.md` from project root if it's not actively used (currently untracked).
- [ ] Review `docs/claude-code-package/` — older audit packages can be archived.
- [ ] Remove `frontend/src/components/voice/` if voice never gets used (currently wired up, but Web Speech API has limited browser support).
- [ ] Migrate `frontend/src/lib/categories.ts` references — if any modules are extracted to their own pages, this might shrink.

---

## ✅ Recently Done (2026-05-31 — Notion SHIPPED to production)

- **Notion integration is LIVE** — merged `feature/notion-integration` → `main` (`--no-ff`, `32ec540`) + pushed; Railway auto-deployed both services. Railway env set: `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, `NOTION_REDIRECT_URI`, `INTEGRATION_TOKEN_KEY` (Fernet — **never rotate** or stored tokens break). User registered a **public** Notion integration. **OAuth connect verified live.**
  - **⏳ Residual:** confirm the end-to-end **push** (Design Kit → Notion page renders) — connect verified, push tested (24 tests) but not live-confirmed this session.
  - **✅ Cleanup done:** `feature/notion-integration` deleted (local + origin, 2026-05-31) after confirming it was fully merged into `main`.
  - **Gotcha:** the first connect click can return "not found" right after a Railway env change/deploy (propagation lag) — a retry works (diagnosed via a prod-callback probe → `307 → ?notion=error`, proving the route was live).

## ✅ Recently Done (2026-05-30 — Notion integration built)

- **Notion integration (OAuth + push design kit)** built on branch `feature/notion-integration` — first provider out of `coming_soon`. Backend `notion_service.py` + 4 routes + 3 `NOTION_*` config vars; frontend `NotionConnectCard` (Settings) + `NotionPushButton` (Design Kit). 24 tests in `test_notion_integration.py`. Backend suite 270 collected across 11 files (265 pass · 1 skip · 4 deselected); frontend 37/37, `tsc`+ESLint clean. **Merged + deployed 2026-05-31 (see above).**
  - Doc-debt fixed in passing: feature #24 in CLAUDE.md + ROADMAP overstated the pre-existing integration scaffold (claimed OAuth routes that never existed) — corrected.

## ✅ Recently Done (2026-05-30 — Discovery v2 SSE streaming tests)

- **`backend/tests/test_discovery_sse.py`** (17 tests: 16 pass + 1 documented skip) — closed the last big v2 backend coverage gap. Covers the two SSE streaming routes (`POST /discovery/{id}/init`, `POST /discovery/{id}/message`) that `test_discovery_v2_integration.py` explicitly deferred. Mocks the AI boundary only; runs flow-version branching, prompt construction, persistence, field-summary aggregation, and SSE event assembly for real. **Test-only — no app logic touched.** Committed to `main` as `06901cf`.

---

## ✅ Recently Done (2026-05-30 — doc governance + deploy fixes + CSP incident)

### Doc governance + vendored directive kit
- Reconciled the Claude-Kit doc directive to root-level SemVer-per-doc (no `docs/` tree); CLAUDE.md "Doc system scope" override (`6812a87`).
- Vendored + `@include`d the binding directives in CLAUDE.md; tracked DEBUG_PROTOCOL / VERSION_CONTROL / SEO_OPTIMIZATION / seo-research-catalog / TESTING_PROCEDURES / SOFTWARE_RELEASE / _CLAUDE-KIT-README; TESTING scoped to Python+React + no-preview; SOFTWARE_RELEASE → N/A stub (`f7eff4c`).
- Corrected repo URL → `github.com/Vybecode-LTD/Ide_AI` (`0f96d48`).
- VERSION_CONTROL pre-commit gate now mandates re-locking after a dependency-manifest edit (`a6862e4`).

### Deploy + production fixes
- **Railway backend build unblocked** — regenerated `backend/poetry.lock` (a `dev` group was added to `pyproject.toml` without re-locking) (`7ce7148`).
- **Production CSP incident (resolved)** — added `clerk.myide.ai` to the CSP (`0e5c7c7`) and the backend ORIGIN to `connect-src` (`c826ad5`) in `frontend/Caddyfile`, with guard comments. Full root-cause in [`CONTEXT_HANDOFF.md`](CONTEXT_HANDOFF.md).
- **Secrets rotated + verified** — all 3 webhook signing secrets + API keys (Clerk/Stripe/Resend); Railway env updated; sign-in confirmed.

### UX
- Home: moved "Start Discovery" above the optional template grid (`a21af70`). `tsc` + 37/37 vitest clean.

---

## ✅ Recently Done (2026-05-27/28 codebase alignment audit + security fixes)

### 12-task Codex codebase alignment audit — all completed
1. Frontend lint blockers fixed (DesignKit hooks split into stable child components)
2. Meaningful-value semantics + v2 Proceed gate
3. Artifact context service — unified v1/v2 bridge (`build_artifact_context()`)
4. Exports + prompt packages use v2 context
5. Blocks / pipeline / market / sprint use v2 context
6. DesignKit action cards — `MODULE_ACTIONS` map
7. Sharing rating contract fixed
8. Entitlement gates on AI-costing routes
9. Auth token readiness (authFetch helper)
10. Module pathway membership validation
11. Stripe billing state hardening (migration 032, webhook lifecycle)
12. Deployment docs / dev deps / docker-compose

### Security fixes (from orchestrator findings)
- **SAST-H2**: OpenAPI docs disabled in production
- **SAST-M1**: Stripe error messages sanitized
- **SAST-M2**: Content-Security-Policy header added

### Test results: 229/229 backend, 37/37 frontend, TypeScript clean.

---

## ✅ Earlier — 2026-05-25 production bug-fixing marathon

### Production bug fixes — 7 bugs found + fixed during live testing

1. **Mobile horizontal overflow in Discovery** — `min-w-0` + `overflow-x-hidden` on flex containers in Discovery.tsx, ChatThread.tsx, QuickChips.tsx.
2. **Premature proceed button** — gated on field completion percentage, disabled below threshold.
3. **Extraction stalling at ~85%** — windowed to last 8 messages + aggressive extraction + "STILL MISSING" section.
4. **Chip relevance overhaul** — replaced keyword-bucket fallback with AI-powered contextual chip generation. Generic-chip blocklist filter. `__type_your_answer__` sentinel. FORBIDDEN chip list in all 4 prompt variants.
5. **PDF transcript export "Network Error"** — `safe_filename_slug()` utility on all 7 export endpoints + try/except on PDF generation.
6. **Proceed button falsely enabled at 85%** — `_has_value()` validator in `compute_field_summary()` + proceed gate on `overall_percent >= 100`.
7. **Design Kit "Continue Discovery" button cut off on mobile** — responsive header + sticky bottom bar + bottom padding.

### 38 regression tests added (`test_chips_and_exports.py`)

Chip parsing (4), generic filter (3), fallback sentinel (2), AI fallback (2), safe slug (12), transcript PDF/TXT/MD (7), field summary _has_value (8). **Total backend: 188/188 pass.**

---

## ✅ Earlier — 2026-05-23/24 marathon sessions

12+ commits across 6 major workstreams. See `CHANGELOG.md` for the full per-commit breakdown.

### Discovery v2 overhaul (Phases 1-6 all shipped + audit closure)
- **Phase 1** (`fb840de`) — module field schemas (40 modules × 154 fields), `projects.flow_version` migration 029, up-front pathway assembly at project creation
- **Phase 2** (`8cfc66a`) — unified discovery prompt + `extract_module_fields` extractor + `field_update` SSE event + service helpers
- **Phase 2 hotfix** (`23f5e7d`) — migration 030 (shape backfill + UNIQUE constraint), race-safe ON CONFLICT upsert, type coercion via `_coerce_field_value`, SSE serialization safety, empty-pathway guard
- **Phase 3** (`94102cb`) — Home reorder (TemplateGrid below partner picker), post-create module-preview overlay, AnimatePresence with per-module stagger
- **Phase 3 hotfix** (`a7257e0`) — 5 audit-found bugs closed: setTimeout leak, billing-success URL category preservation, template projects flagged `flow_version='v1'`, Library resume routing branches on flow_version, PathwayReview redirects v2 to Discovery
- **Phase 4** — `ProgressPanel` on right side of Discovery for v2, `useSSE` extended with `onFieldUpdate` callback, Discovery branches on `flow_version`, v2 Proceed gate replaces confidence_score check, module-preview overlay a11y improvements
- **Phase 4 audit closure** (this commit) — 14 audit findings resolved in one sweep:
  - **H1** `projects.py` downgrades v2→v1 when assembly skipped (closes stranded-user state)
  - **H2** `PathwayExecute.tsx` v2 redirect (defense-in-depth)
  - **M1** extraction prompt instructs dict fields to return whole object (mitigates JSONB shallow-merge)
  - **M2/L3** stage UI hidden for v2 (TopBar subtitle + StagesStepper + mobile indicator)
  - **M3** `build_unified_greeting_prompt` for v2 init handler (references assembled modules)
  - **M4** `loadSheet()` skipped for v2 (consolidated bootstrap effect)
  - **M5/L2** ProgressPanel expanded-set FIFO-capped at 3 modules
  - **M6** new `GET /discovery/{session_id}/field-summary` endpoint + frontend hydration
  - **M7** `_coerce_field_value` drops now logged with module/field/value context
  - **M8** Proceed gate uses `total_fields > 0` (handles all-optional pathways)
  - **L1** `recentUpdates` highlight auto-fades after 8s
  - **L5** `_reset_module_library()` test hook
  - **I4** new `test_discovery_v2.py` — 35 tests, 76/76 backend tests pass
  - **Defensive bonus** — `apply_extracted_module_fields` now rejects unknown field keys (gap caught by new test suite)
- **2-agent audit** ran between Phase 2 and the hotfix — caught the modules-shape blocker plus 4 defensive bugs
- **Self-audit** at end of Phase 4 — identified all 15 actionable items, all resolved
- Backend + frontend foundation ready for Phase 5 (Design Kit page) and Phase 6 (additional discovery for added modules)

### Discovery SSE robustness (`e33c7a6`)
- Assistant message now persists in its own transaction (resume bug fixed)
- `done` event always fires with chip fallback (intermittent dropouts fixed)
- Same defensive treatment applied to `/discovery/{id}/init`

### Realtime inbox (`64a87bf`, verified)
- Redis pub/sub backed SSE stream at `/inbox/stream`
- Auto-reconnect with exponential backoff (1s → 30s)
- Graceful 503 fallback when `REDIS_URL` is empty
- Multi-tab realtime confirmed working in production

### Admin system (`3747eac`, user-tested)
- Hidden `/admin` route gated by `users.is_admin`
- Migrations 027 + 028 (is_admin, entitlement_overrides, admin_audit_log)
- Full CRUD on user plans / overrides / admin flag via UI drawer
- Audit log of every action
- Bootstrap via SQL `UPDATE users SET is_admin = TRUE WHERE id = '<id from /auth/me>'`

### Doc versioning (`6599cd1` + `4032cbc`)
- DOC_VERSIONING.md convention + CHANGELOG.md + frontmatter on all versioned docs
- Stop hook at `.claude/hooks/check-doc-versioning.sh` nags on missing CHANGELOG
- Project memory entries for `admin-system`, `doc-versioning`, `duplicate-user-rows`

### Roadmap refresh (`ec1e0a2`)
- Recently Shipped section, Up Next queue formalized

### Toast migration (`28ead2d`)
- ~40 silent failures surfaced via `toast.error(extractError(err, fallback))` across 18 components
- `fetchPathway()` unhandled rejections wrapped in ModuleSession + PathwayExecute
- Inline error banners removed from Profile, CommentSection, StarRating, billing/UpgradeModal
