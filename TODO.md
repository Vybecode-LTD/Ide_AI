# Ide/AI — TODO

> **Version:** 3.6.0 · **Last updated:** 2026-05-25 · See [CHANGELOG.md](CHANGELOG.md)
>
> Concrete actionable items. See [`ROADMAP.md`](ROADMAP.md) for strategic direction, [`CONTEXT_HANDOFF.md`](CONTEXT_HANDOFF.md) for current-session state + the **Regression Test Matrix** (which code path is protected by which test file), and [`MEMORY.md`](MEMORY.md) for conventions + recent-session signature.

---

## 🔴 P0 — DO FIRST (before any new development)

- [x] **`git push origin main`** — ✅ DONE 2026-05-23 (5 commits) + 2026-05-25 (5 more commits). Railway auto-deploys both services on push.
- [ ] **Commit + push latest changes** — 6 files changed (proceed button _has_value fix, Design Kit mobile layout, 8 new tests, doc updates). Commit, push, verify Railway deploy.
- [ ] **5-minute production smoke test** after Railway confirms healthy:
  - Happy v2 path: open https://myide.ai → pick a category → describe an idea → Start Discovery. Verify chips match the AI's question (not generic), ProgressPanel updates, field_update SSE fires.
  - Proceed gate: confirm button stays disabled below 100% overall_percent. Badge shows `N% complete`.
  - `__type_your_answer__` sentinel: for open-ended questions, verify the amber "Type your answer below" indicator appears.
  - Design Kit mobile: verify "Continue Discovery" sticky bottom bar is visible, header buttons don't overflow.
  - Export: verify PDF/TXT/MD transcript downloads without "Network Error".
  - Check Railway logs for any 500s or errors.
- [ ] **Rotate 3 webhook signing secrets** — `CLERK_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`, `RESEND_WEBHOOK_SECRET` were pasted in chat. Roll each in its origin dashboard (Clerk/Stripe/Resend → Webhooks → Roll/Regenerate), update Railway env vars, send a "Send example" → 200.

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

- [ ] **Rotate 3 webhook signing secrets** — `CLERK_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`, `RESEND_WEBHOOK_SECRET` were pasted in chat during the 2026-05-23 setup session. Each can be rolled in its origin dashboard (Clerk/Stripe/Resend → Webhooks → Roll/Regenerate signing secret), then updated in Railway. Test after rotation: send a "Send example" webhook → backend log returns 200, not 401.

---

## 🟡 HIGH PRIORITY

### Remaining toast migrations (light)
Most error sites are now toast-surfaced (commit `28ead2d`). What's left:

- [x] ~~**`Home.tsx`** — `createError` state → `toast.error(extractError(...))`~~ — **DONE**.
- [x] ~~**`SprintPlanner.tsx`** — removed `errorMessage` state, unified on `toast.error()`~~ — **DONE**.
- [ ] **`pathwayStore.ts`** and **`ErrorBoundary.tsx`** intentionally left as `console.error` — both are framework-level, not user-facing. No change needed.

### Test coverage

> Before adding tests, check the **Regression Test Matrix** in [`CONTEXT_HANDOFF.md`](CONTEXT_HANDOFF.md) — it lists every code path currently covered (**188 backend tests across 7 files + 31 frontend tests across 4 files = 219 total**) and the explicit gaps. Avoid duplicating coverage.

- [x] ~~**Frontend tests** — Vitest setup + first tests~~ — **DONE**. 31 tests across 4 files.
- [x] ~~**Backend admin endpoint tests**~~ — **DONE**. 27 tests in `test_admin.py`.
- [x] ~~**Discovery v2 endpoint integration tests**~~ — **DONE**. 34 tests in `test_discovery_v2_integration.py`.
- [x] ~~**Chip relevance + export + field summary tests**~~ — **DONE 2026-05-25**. 38 tests in `test_chips_and_exports.py`: chip parsing (4), generic filter (3), fallback sentinel (2), AI fallback (2), safe slug (12), transcript PDF/TXT/MD (7), field summary _has_value (8).
- [ ] **Discovery v2 SSE streaming tests** — `/discovery/{id}/init` v2-vs-v1 prompt branching + `/discovery/{id}/message` field_update emission. Requires mocking `AsyncAnthropic.messages.stream` with a canned token sequence. ~2h. Closes the last big v2 backend coverage gap.
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
- [ ] **Update `DEPLOYMENT_RAILWAY.md`** with the 4 env vars from the BLOCKING section above.

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

## ✅ Recently Done (2026-05-25 production bug-fixing marathon)

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
