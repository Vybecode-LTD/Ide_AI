# Ide/AI — TODO

> **Version:** 2.0.0 · **Last updated:** 2026-05-23 · See [CHANGELOG.md](CHANGELOG.md)
>
> Concrete actionable items. See `ROADMAP.md` for strategic direction.

---

## 🔴 BLOCKING

_Nothing currently blocking. Railway env vars are set, sign-in works end-to-end, admin system ships with bootstrap path._

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

## ✅ Recently Done (2026-05-23)

See `CHANGELOG.md` and `CONTEXT_HANDOFF.md` for full session details. Highlights:

### Admin system (commit `3747eac`)
- Hidden `/admin` route gated by `users.is_admin`
- Migrations 027 + 028 (is_admin, entitlement_overrides, admin_audit_log)
- Full CRUD on user plans / overrides / admin flag via UI drawer
- Append-only audit log of every admin action
- `entitlement_service.get_limits()` merges overrides over plan defaults
- Bootstrap path documented in [admin-system memory](.claude/memory/admin-system.md)

### Toast migration (commit `28ead2d`)
- ~40 silent failures surfaced via `toast.error(extractError(err, fallback))` across 18 components
- `fetchPathway()` unhandled rejections wrapped in `ModuleSession` + `PathwayExecute`
- Inline error banners removed from Profile, CommentSection, StarRating, billing/UpgradeModal
- `toast.success()` on import / snapshot / share-link / comment milestones

### Railway production hardening
- `CORS_ORIGINS` set (JSON array for both apex + www)
- `CLERK_ISSUER` set (`https://clerk.myide.ai`, custom-domain Clerk)
- `CLERK_AUTHORIZED_PARTIES` set (JSON array, blocks token replay)
- All 3 webhook secrets verified (sign-in confirmed working post-hardening)

### Doc versioning (this commit)
- `DOC_VERSIONING.md` — SemVer per doc convention + bump rules + CHANGELOG entry checklist
- `CHANGELOG.md` — Keep-a-Changelog format, backfilled with recent history
- Frontmatter (Version + Last updated + CHANGELOG link) on CLAUDE.md, CONTEXT_HANDOFF.md, TODO.md, DOC_VERSIONING.md

### Earlier 2026-05-23 (pre-admin)
- All 15 audit tasks closed with 2-agent verification per fix
- Mobile viewport conformance across 19 pages
- Proceed button errors now surface to user
- `auth.py` race handling consolidated with INSERT ON CONFLICT
- react-hot-toast wired globally
- Drag-and-drop Blocks, voice mic, PitchMode flow diagram, inbox per-item partner picker
