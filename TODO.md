# Ide/AI — TODO

> Concrete actionable items. See `ROADMAP.md` for strategic direction.
> **Last updated:** 2026-05-23

---

## 🔴 BLOCKING (Must do before launch)

### Railway deployment configuration
> These need to be set in Railway's backend service env-var panel. No code changes — just paste values.

- [ ] **`CORS_ORIGINS`** = `["https://myide.ai","https://www.myide.ai"]`
  - Without this, ALL authenticated requests fail because browser blocks CORS.
  - Default in `config.py` is only `localhost:5173`.

- [ ] **`CLERK_ISSUER`** = your Clerk instance URL (e.g. `https://clean-fox-89.clerk.accounts.dev`)
- [ ] **`CLERK_AUDIENCE`** = your app's audience claim (check Clerk dashboard → JWT templates)
- [ ] **`CLERK_AUTHORIZED_PARTIES`** = `https://myide.ai,https://www.myide.ai`
  - Without these 3, any RS256 JWT from any Clerk instance validates against your backend.

- [ ] **Verify webhook secrets are set:**
  - `CLERK_WEBHOOK_SECRET` (from Clerk → Webhooks → endpoint signing secret)
  - `STRIPE_WEBHOOK_SECRET` (from Stripe → Developers → Webhooks)
  - `RESEND_WEBHOOK_SECRET` (from Resend → Inbound → Webhook signing secret)

---

## 🟡 HIGH PRIORITY (Polish before broad announcement)

### Unhandled promise rejections (2 sites)
- [ ] **`frontend/src/pages/ModuleSession.tsx:73`** — calls `fetchPathway(projectId)` without try/catch. Store now re-throws on all errors including 404. Wrap:
  ```ts
  try { await fetchPathway(projectId) } catch (err) {
    const status = (err as any)?.response?.status
    if (status !== 404) toast.error('Failed to load pathway')
  }
  ```
- [ ] **`frontend/src/pages/PathwayExecute.tsx:43`** — same fix.

### Silent failures with no user feedback (5 high-value pages)
- [ ] **`Discovery.tsx`** — 8 `console.error` sites: SSE error, auto-save, visibility save, unmount save, stage-change save, session start, partner switch, Save Place. Replace with `toast.error()` for user-facing ones (auto-saves can stay silent).
- [ ] **`Blocks.tsx`** — 5 `console.error` sites: fetch, generate, update, delete, persist order. All user-initiated — surface via toast.
- [ ] **`Library.tsx`, `Pipeline.tsx`, `Exports.tsx`, `PromptKit.tsx`** — convert their `console.error` patterns.
- [ ] **`MarketAnalysis.tsx`, `SprintPlanner.tsx`** — SSE error paths.

### Setstate → toast migration
- [ ] **`Profile.tsx`** — 4 `setError` calls (save, avatar upload, billing portal).
- [ ] **`SharedProject.tsx`** — 4 `setError` calls (expired, not-found, load errors).
- [ ] **`Home.tsx`** — `createError` state on project creation (line 51).
- [ ] **`components/sharing/CommentSection.tsx`** — 3 `setError`.
- [ ] **`components/sharing/StarRating.tsx`** — 3 `setError`.
- [ ] **`components/billing/UpgradeModal.tsx`** — checkout failure.

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

See `CONTEXT_HANDOFF.md` for full session summary. Highlights:
- All 15 audit tasks closed with 2-agent verification per fix
- Mobile viewport conformance across 19 pages
- Proceed button errors now surface to user
- auth.py race handling consolidated with INSERT ON CONFLICT
- react-hot-toast wired globally
- Drag-and-drop Blocks, voice mic, PitchMode flow diagram, inbox per-item partner picker — all shipped
