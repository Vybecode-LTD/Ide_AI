# Ide/AI — TODO

> **Version:** 3.3.1 · **Last updated:** 2026-05-23 · See [CHANGELOG.md](CHANGELOG.md)
>
> Concrete actionable items. See `ROADMAP.md` for strategic direction.

---

## 🔴 P0 — DO TODAY (before any new development)

These three items unblock production users. The first is the most urgent — until the commits are pushed, the H1 greenlet bug fix is dormant and any user creating a v2 project without a category hits a 500.

- [ ] **`git push origin main`** — 3 commits sit locally on `main` (`b26837a` Phase 4 features, `ff212f3` audit closure + 35 tests, `57aa9d3` integration tests + H1 greenlet fix). Railway auto-deploys both services on push. The H1 fix is a real production bug — every H1-downgraded project (POST /projects without `primary_category`, or with a failing assembly) would have hit a 500 on the response. **Push before anything else.**
- [ ] **5-minute production smoke test** after Railway deploys:
  - Happy v2 path: open https://myide.ai → pick a category → describe an idea → Start Discovery. Verify the 2.2s module-preview overlay appears, ProgressPanel renders on the right of Discovery, AI greeting references modules, field_update fires after each user reply.
  - H1 in the wild: check Railway logs for `MissingGreenlet` or `ResponseValidationError` over the past 48h. If anyone hit it pre-fix, they'll be there.
  - H2 in the wild: manually deep-link to `/pathway-execute/{any-v2-pid}` and confirm it redirects to `/discovery/`.
- [ ] **Rotate 3 webhook signing secrets** — `CLERK_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`, `RESEND_WEBHOOK_SECRET` were pasted in chat during the 2026-05-23 setup session. Roll each in its origin dashboard (Clerk/Stripe/Resend → Webhooks → Roll/Regenerate signing secret), update Railway env vars, send a "Send example" webhook to each to verify it still validates (200 not 401).

---

## 🚦 Phase 5 — Design Kit page at /design-kit/{projectId} (next active work)

Phase 4 + audit closure + integration tests are all shipped. Phase 5 builds the final v2 destination — a per-project Design Kit view that replaces `/exports/{id}` as the Proceed target.

**Recommended sequencing** (not a strict gate, but the order that protects you from regressions):

1. **First, land the Vitest scaffold + 4-5 frontend tests** (currently in HIGH PRIORITY → Test coverage below). The Phase 5 forms + optimistic updates + refresh affordances are non-trivial frontend complexity, and there's zero Vitest coverage today. Landing the scaffold + first tests as item zero of Phase 5 means subsequent work is testable from day one. Skip this and you'll discover bugs only on Railway.
2. **Then the Design Kit page shell + Edit affordance + PATCH endpoint** (items 1-3 below) — the core user-visible value.
3. **Then swap the Proceed destination + update Library resume routing** (items 6-7) — small but visible. Do these together so v2 users immediately benefit.
4. **Then Refresh + Add Modules** (items 4-5) — polish that completes Phase 5.

For each new endpoint added in Phase 5, **add a matching integration test in `test_discovery_v2_integration.py`** before declaring the task done. The integration suite caught the H1 greenlet bug — keep that habit.

- [ ] **1. `pages/DesignKit.tsx` + route** at `/design-kit/:projectId`. Each assembled module renders as a card with its current field values + an Edit button. Use the `field_summary` shape from M6 endpoint to hydrate.
- [ ] **2. Per-module Edit affordance** — inline form per module showing every field schema (label / type / required indicator). Save dispatches PATCH to the new backend endpoint that writes into `module_responses.responses`. Field-type-aware inputs (text/longtext/list-as-chips/dict-as-key-value-rows).
- [ ] **3. Backend: `PATCH /api/v1/modules/{project_id}/{module_id}/responses`** — partial-update fields on a module response. Validates keys against the module's `fields` schema. **Must reuse `_coerce_field_value` for type safety AND the defensive unknown-field-key rejection pattern added in `apply_extracted_module_fields`** — same defense, two surfaces.
- [ ] **4. Refresh affordance for `has_output` modules** — 6 of the 40 modules have `has_output: true`. UI: "Regenerate output" button per such module card. Backend: `POST /api/v1/modules/{project_id}/{module_id}/refresh-output` runs the existing module-output prompt builder against the current responses. Returns 400 for non-has_output modules.
- [ ] **5. "Add Modules" button** at the top — opens a category-filtered picker (reuses the module library data via existing endpoint). Selected modules append to `module_pathways.modules`. New backend: `POST /api/v1/projects/{project_id}/pathway/modules` for the append operation. Phase 6 picks up newly-added unfilled modules.
- [ ] **6. Swap the v2 Proceed destination** in `Discovery.tsx` from `/exports/{id}` to `/design-kit/{id}` once item 1 lands. Existing M8 test covers Proceed rendering — no new test needed.
- [ ] **7. Update Library resume routing** in `backend/app/routers/library.py:_compute_resume_path` — v2 projects whose pathway has all-required fields filled should resume to `/design-kit/{id}` instead of `/discovery/{id}`. Extend `TestLibraryResumeRouting.test_v2_project_resumes_to_discovery` with completed-summary cases routing to design-kit.

---

## 🧭 Phase 6 — Additional Discovery for newly-added modules (after Phase 5)

- [ ] **Mini-Discovery flow** scoped to just the new modules' unfilled fields. Reuses the unified-discovery prompt builder but filters `pathway_modules` to only the newly-added IDs.
- [ ] **"Continue Discovery" button** on Design Kit when there are unfilled required fields on recently-added modules.
- [ ] Field updates feed back into `module_responses` via the existing apply path — no new backend infra required.

---

## 🛡 Security hygiene (recommended)

- [ ] **Rotate 3 webhook signing secrets** — `CLERK_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`, `RESEND_WEBHOOK_SECRET` were pasted in chat during the 2026-05-23 setup session. Each can be rolled in its origin dashboard (Clerk/Stripe/Resend → Webhooks → Roll/Regenerate signing secret), then updated in Railway. Test after rotation: send a "Send example" webhook → backend log returns 200, not 401.

---

## 🟡 HIGH PRIORITY

### Remaining toast migrations (light)
Most error sites are now toast-surfaced (commit `28ead2d`). What's left:

- [ ] **`Home.tsx`** — `createError` state on project creation (line 51) still uses inline. Convert to toast for consistency.
- [ ] **`SprintPlanner.tsx`** — has `errorMessage` state kept alongside toast for sticky display during 60s+ generation. Consider whether to remove the sticky state now that toast is in place.
- [ ] **`pathwayStore.ts`** and **`ErrorBoundary.tsx`** intentionally left as `console.error` — both are framework-level, not user-facing. No change needed.

### Test coverage
- [ ] **Frontend tests** — Vitest setup + first tests for `extractError`, `inboxStore.adjust(-1)` clamping, `adminStore` mutation behaviour, `useSSE` safety-net `onDone`, `useSSE` `field_update` parsing, `ProgressPanel` expanded-set FIFO cap.
- [ ] **Backend admin endpoint tests** — `require_admin` rejection on non-admin user; `update_user_plan` audit log entry; `update_user_admin_flag` self-revoke block; entitlement override merge logic.
- [ ] **Discovery v2 endpoint integration tests** — `GET /discovery/{session_id}/field-summary` (200 for v2, 409 for v1, 404 for missing); init handler v2 vs v1 prompt branching; H1 fix: POST /projects without primary_category persists flow_version='v1'. Needs FastAPI TestClient setup.
- [ ] **Discovery v2 upsert tests** — `apply_extracted_module_fields` ON CONFLICT path requires PostgreSQL — out-of-scope for the SQLite test harness. Either add a PG-backed integration test environment or document as production-verified-only.

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

### Frontend (currently zero tests)
- [ ] Vitest setup + first test (extractError function — pure, no UI)
- [ ] `inboxStore.adjust(-1)` clamps at 0 (no negative counts)
- [ ] `useSSE` hook safety-net fires `onDone` when stream ends without done event
- [ ] `PathwayReview.init()` 404 path doesn't show error toast

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

## ✅ Recently Done (2026-05-23 marathon session)

12 commits shipped today. See `CHANGELOG.md` for the full per-commit breakdown.

### Discovery v2 overhaul (Phases 1-4 of 6 shipped + full audit closure)
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
