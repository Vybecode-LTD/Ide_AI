# Ide/AI — Roadmap

> Forward-looking priorities. See `TODO.md` for concrete actionable items.
> **Last updated:** 2026-05-23

---

## 🚀 Launch Readiness (Now)

The codebase itself is launch-ready. Only deployment-side configuration remains.

### Pre-launch checklist (Railway dashboard, no code changes)
- [ ] Set `CORS_ORIGINS=["https://myide.ai","https://www.myide.ai"]` in backend env
- [ ] Set `CLERK_ISSUER`, `CLERK_AUDIENCE`, `CLERK_AUTHORIZED_PARTIES` for JWT hardening
- [ ] Verify `STRIPE_WEBHOOK_SECRET` matches the webhook endpoint configured in Stripe dashboard
- [ ] Verify `RESEND_WEBHOOK_SECRET` matches Resend's inbound parse webhook config
- [ ] Verify `CLERK_WEBHOOK_SECRET` matches Clerk's webhook config
- [ ] Verify all 4 `STRIPE_PRICE_*` env vars match live Stripe price IDs
- [ ] Confirm `INBOX_DOMAIN` MX records point to Resend's inbound parser
- [ ] Generate + set `INTEGRATION_TOKEN_KEY` if/when integrations get re-enabled (currently `coming_soon`)

### Smoke-test checklist (post-deploy)
- [ ] Sign up via Clerk → confirm user row created in DB
- [ ] Create project → verify pathway auto-detected from idea description
- [ ] Run full discovery → verify chips appear, sheet updates in real-time, no AI repetition
- [ ] Save Place button works
- [ ] Proceed → PathwayReview loads modules → confirm → execute
- [ ] Export transcript (copy + PDF) — both roles present in output
- [ ] Mobile: pinch-zoom disabled, viewport fills correctly, TopBar chips scroll, bottom nav doesn't overlap content on iPhone
- [ ] Hit project limit on free plan → EntitlementLimitModal appears
- [ ] Click "View Plans" → goes to pricing → Stripe checkout works → webhook updates `account_type`

---

## 🎯 Short-Term Polish (Next 1-2 sessions)

### UX consistency
- **Unify error UX** — ~17 sites still use `setError` or silent `console.error`. Migrate to `toast.error()` for consistency. High-value targets in priority order:
  1. `Discovery.tsx` (8 silent failures around SSE + auto-save)
  2. `Blocks.tsx` (5 silent failures around generate/update/delete)
  3. `Library.tsx`, `Pipeline.tsx`, `Exports.tsx`, `PromptKit.tsx`
  4. `PitchMode.tsx`, `ModuleSession.tsx`, `MarketAnalysis.tsx`, `PathwayReview.tsx`
  5. `Profile.tsx`, `SharedProject.tsx`, `SprintPlanner.tsx` (still use `setError` with inline banners)
- **Wrap unhandled promise rejections** — `ModuleSession.tsx:73` and `PathwayExecute.tsx:43` call `fetchPathway()` without try/catch. Now that the store re-throws, these need protection.
- **Cross-tab inbox badge sync** — Sidebar polls every 60s but ignores `storage` events / BroadcastChannel. Add a `storage` listener so tab A adding an idea immediately bumps tab B's badge.

### Code organization
- **Hoist `_partnerCache`** to `frontend/src/lib/partnerCache.ts`. Currently duplicated in `Home.tsx` and `Inbox.tsx`.
- **Centralize the optimistic-update pattern** used by inboxStore for future stores (toggle adjust + reconcile).
- **Add backend tests for the auth refactor** — `_idempotent_create_user` + `_link_existing_email_user`. Test the 4 race scenarios end-to-end with the new INSERT ON CONFLICT path.

### Performance
- **Lazy-load reactflow CSS** alongside the PitchMode bundle (currently included in the lazy chunk; ~150KB total).
- **Module-pathway store** doesn't memoize selectors — components re-render on every `loading` change even when only `pathway` is needed.

---

## 🎁 Medium-Term Features (Next 5-10 sessions)

### Discovery experience
- **Realtime inbox via WebSocket or SSE** — replace 60s polling with push notifications. Backend infra is FastAPI + StreamingResponse — straightforward.
- **Voice transcript export** — capture full voice input as part of transcript metadata.
- **AI partner mid-session preview** — show what the next AI response would look like in each partner's voice before switching.
- **Discovery progress bar** — visualize stage progression more prominently than the side stepper.

### Modular pathway
- **Module dependencies / prerequisites** — currently any order is valid. Add optional `requires` field to module definitions.
- **Cross-module reference UI** — when AI mentions a field already answered, highlight which module/answer it's coming from.
- **Module library expansion** — currently 47 modules across 7 groups. Expand to 70-100 to cover more pathways.
- **Pathway templates** — save a custom pathway configuration and reuse for similar future projects.

### Sharing & collaboration
- **Realtime collaborative editing on shared projects** — partner reviews while owner iterates.
- **Email digest of share comments** — daily digest of new comments/ratings.
- **Public showcase** — opt-in gallery of completed projects (with owner approval).

### Integrations (currently de-scoped as `coming_soon`)
- **Notion** — push design sheet + blocks to a Notion page hierarchy
- **Trello / Linear** — convert MVP blocks to cards/issues
- **Figma** — generate FigJam wireframe from UI skeleton
- **Google Docs** — export Pitch document
- **Airtable** — sync block list to a base

### Billing
- **Usage-based add-ons** — extra projects, AI tokens, market analyses
- **Team plan** — multi-user workspaces with shared projects
- **Annual discount surfacing** — currently in code but could be more prominent

---

## 🔭 Long-Term Vision (When/If)

- **Native mobile apps** (React Native + Expo) — current web mobile is functional but a native app would unlock voice-first usage
- **Multi-language support** — discovery in Spanish, French, German, Mandarin
- **AI model selection** — let users choose Claude variants (Haiku for speed vs Opus for depth) per project
- **Custom AI partners** — let users define their own partner persona with a structured config
- **Pathway marketplace** — community-contributed pathways for niche industries (legal, biotech, edtech)
- **Versioned exports** — git-like history of design kits, with diffs
- **Plugin SDK** — let third parties build extensions that consume the design kit format

---

## 🧹 Tech Debt & Refactors

### Backend
- **Replace `inbox.py` lazy import of `validate_partner_style`** with module-level import (no circular import risk; was defensive but unnecessary).
- **Migrate from `datetime.utcnow()`** — already done across 7 files; audit one more pass to catch any new usage.
- **SQLite test fixtures** — `conftest.py` has JSONB/UUID compat shims. Replace with PostgreSQL testcontainers for higher fidelity.
- **Anthropic SDK pinning** — currently uses untyped Anthropic calls in some places. Migrate to typed `messages.create()` everywhere.
- **Reduce N+1 queries** in `library.py` `_compute_resume_path` — currently issues one query per project. Add eager loading.

### Frontend
- **Consolidate the 2 `_partnerCache` duplicates** (Home + Inbox).
- **Replace `react-router-dom` with TanStack Router** — when/if we want type-safe routing.
- **Migrate ReactFlow to lazy chunk** if PitchMode bundle size becomes an issue.
- **Add ESLint rule to forbid `console.error`** for user-facing failures — should always be `toast.error()`.
- **Add ESLint rule to forbid `h-screen` in pages** — should be `.h-dvh` for mobile compatibility.
- **Storybook** for the design system components (Button, Card, Badge, Modal, etc.).
- **Vitest + React Testing Library** — currently zero frontend tests. Highest-leverage targets: useSSE hook, inboxStore, extractError, PathwayReview init flow.

### Infrastructure
- **Sentry / error tracking** — currently relies on Railway logs.
- **Performance monitoring** — backend latency, AI call duration, p99 response times.
- **Database query observability** — slow query log.
- **Backup automation** — Railway has snapshots but no automated weekly export.

---

## 📊 Metrics Worth Tracking (When We Have Users)

- **Activation funnel**: signup → first project → first discovery message → first block generated → first export
- **Retention**: D1, D7, D30 active users
- **Pathway completion rate**: % of users who lock a pathway after discovery
- **Module completion rate**: per-module deep-vs-lite usage
- **Voice usage**: % of discovery sessions that use the mic
- **Plan conversion**: free → basic, basic → pro
- **Partner style preference distribution**: which of the 10 partners users actually pick
- **Top template categories**: which of the 16 categories drive most projects
- **Inbound email engagement**: ratio of inbox items captured vs promoted

---

## ❓ Open Product Questions

1. **Should the AI partner be visible to viewers on shared projects?** Currently hidden — but partner style affects the design output, so it's relevant context.
2. **Should we support multiple AI partners per project?** Currently one per session, switchable mid-flow. Could one project have separate partners per module?
3. **Should categorize/assemble be re-runnable?** Currently fires once on PathwayReview mount. If user adds significant detail after, they can't re-trigger.
4. **Mobile-first redesign?** Current design is desktop-first with mobile responsive. Worth a full mobile-first pass given voice + email-to-inbox flows are mobile-friendly.
5. **Free tier limits**: 3 projects feels tight. Should we expand to 5 with a "lite" feature set (e.g. no market analysis on free)?
