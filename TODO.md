# Ide/AI — TODO

> **Version:** 3.0.0 · **Last updated:** 2026-05-23 · See [CHANGELOG.md](CHANGELOG.md)
>
> Concrete actionable items. See `ROADMAP.md` for strategic direction.

---

## 🔴 BLOCKING

_Nothing currently blocking. v2 backend foundation is solid; Phase 3 frontend is the next development slice, not a blocker._

---

## 🚦 Phase 3 — frontend Home category + project creation (next active work)

The Discovery v2 backend is ready but project creation doesn't currently pass `primary_category`, which means assembly skips and v2 projects fall back to v1 behavior. Phase 3 wires this.

- [ ] Add a **category selector grid** at the top of Home.tsx — 16 categories grouped by group (software, food, film, fashion, etc.). 4×4 glassmorphism card grid.
- [ ] Default category to user's previous pick (localStorage) for fast iteration.
- [ ] **Pass `primary_category` in the POST /projects payload** — currently nullable, causes v2 assembly to no-op.
- [ ] Optionally pass `secondary_category` based on AI inference from idea description (audit minor — enrichment rule unreachable otherwise).
- [ ] Filter template grid to category-relevant templates when a category is picked.
- [ ] **Brief module preview after project creation** — fetch `/projects/{id}/pathway`, show "Modules we picked: [list]" for 2-3 seconds, then route to Discovery. Optional polish.

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
- [ ] **Frontend tests** — Vitest setup + first tests for `extractError`, `inboxStore.adjust(-1)` clamping, `adminStore` mutation behaviour, `useSSE` safety-net `onDone`.
- [ ] **Backend admin endpoint tests** — `require_admin` rejection on non-admin user; `update_user_plan` audit log entry; `update_user_admin_flag` self-revoke block; entitlement override merge logic.

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

## 🧭 Phase 4+ (Discovery v2 remaining frontend)

After Phase 3 lands, the frontend still needs:

- [ ] **Phase 4 — ProgressPanel** on the right side of Discovery. Replace DesignSheetPanel for v2 projects. Subscribe to `field_update` SSE events. Show overall % + expandable per-module breakdown. Proceed button always available (with warning chip when <80%).
- [ ] **Phase 5 — Design Kit view** at `/design-kit/{projectId}`. Replaces `/exports` as the final destination for v2 projects. Each module: Edit button (inline form per field schema) + Refresh button (only for `has_output` modules). Add Modules button at top → category-filtered picker.
- [ ] **Phase 6 — Additional discovery** for newly-added modules. Mini-Discovery scoped to just the new modules' fields. Integrates back into the design kit on completion.

---

## ✅ Recently Done (2026-05-23 marathon session)

10 commits shipped today. See `CHANGELOG.md` for the full per-commit breakdown.

### Discovery v2 overhaul (Phases 1-2-hotfix shipped)
- **Phase 1** (`fb840de`) — module field schemas (40 modules × 154 fields), `projects.flow_version` migration 029, up-front pathway assembly at project creation
- **Phase 2** (`8cfc66a`) — unified discovery prompt + `extract_module_fields` extractor + `field_update` SSE event + service helpers
- **Phase 2 hotfix** (`23f5e7d`) — migration 030 (shape backfill + UNIQUE constraint), race-safe ON CONFLICT upsert, type coercion via `_coerce_field_value`, SSE serialization safety, empty-pathway guard
- **2-agent audit** ran between Phase 2 and the hotfix — caught the modules-shape blocker plus 4 defensive bugs
- Backend ready for Phase 3 frontend work

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
