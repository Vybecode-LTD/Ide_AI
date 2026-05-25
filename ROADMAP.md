# Ide/AI — Roadmap

> **Version:** 2.2.0 · **Last updated:** 2026-05-23 · See [CHANGELOG.md](CHANGELOG.md)
>
> Forward-looking priorities. See [`TODO.md`](TODO.md) for concrete actionable items, [`CONTEXT_HANDOFF.md`](CONTEXT_HANDOFF.md) for current-session state, and [`CHANGELOG.md`](CHANGELOG.md) for what already shipped.

---

## ✅ Recently Shipped (2026-05-23 marathon session)

**Discovery v2 overhaul — Phases 1-4 + audit closure + integration tests all shipped today.** This is the big-ticket item. v1 backward-compat fully preserved, 91/91 backend tests pass, frontend TypeScript build clean.

- **Phase 1** (commit `fb840de`) — module field schemas (40 modules × 154 fields), `projects.flow_version` migration 029, up-front pathway assembly at project creation
- **Phase 2** (commit `8cfc66a`) — unified discovery prompt + `extract_module_fields` extractor + `field_update` SSE event + service helpers
- **Phase 2 hotfix** (commit `23f5e7d`) — migration 030 (shape backfill + UNIQUE constraint), race-safe ON CONFLICT upsert, type coercion, SSE serialization safety
- **Phase 3** (commit `94102cb`) — Home reorder (TemplateGrid below partner picker), post-create module-preview overlay
- **Phase 3 hotfix** (commit `a7257e0`) — 5 audit-found bugs closed (setTimeout leak, billing URL preservation, template v1 flag, Library resume branching, PathwayReview v2 redirect)
- **Phase 4** (commit `b26837a`) — `ProgressPanel` for v2, `useSSE.onFieldUpdate`, Discovery branches on `flow_version`, v2 Proceed gate routes to `/exports/{id}`, module-preview overlay a11y
- **Phase 4 audit closure** (commit `ff212f3`) — 15 audit findings resolved (H1+H2+M*+L*), 35 unit tests added, defensive unknown-field-key rejection
- **HTTP integration tests + H1 prod-bug fix** (commit `57aa9d3`) — 15 FastAPI TestClient tests caught a real greenlet-during-serialization bug in `projects.py` H1 path (added `await db.refresh(project)` after the downgrade)
- **Doc lockdown** (commit `f8d3165`) — P0 block + Phase 5 sequencing + regression test matrix for fresh-session pickup

**Other 2026-05-23 wins (earlier in the session):**
- **Realtime inbox** — SSE stream at `/inbox/stream` backed by Redis pub/sub. Replaces 60s polling. Graceful 503 fallback when `REDIS_URL` is empty.
- **Admin dashboard** at hidden `/admin` route — user search, plan controls, entitlement overrides, audit log (commit `3747eac`)
- **Toast migration** — ~40 silent failures surfaced via `react-hot-toast` across 18 components (commit `28ead2d`)
- **Doc-versioning system** — SemVer per doc, root CHANGELOG, Stop hook, project memory (commits `6599cd1`, `4032cbc`)
- **Railway production hardening** — `CORS_ORIGINS`, `CLERK_ISSUER`, `CLERK_AUTHORIZED_PARTIES` env vars active; sign-in verified end-to-end

See [`CHANGELOG.md`](CHANGELOG.md) for the full per-commit breakdown and [`CONTEXT_HANDOFF.md`](CONTEXT_HANDOFF.md) for the current-state snapshot.

---

## 🚀 Launch Readiness (Now)

The codebase is launch-ready. The pre-deploy checklist is essentially done — what remains is post-deploy smoke verification with a real user.

### Optional security hygiene
- [ ] Rotate the 3 webhook signing secrets (Clerk / Stripe / Resend) — they were pasted in chat during the 2026-05-23 setup session
- [ ] Generate + set `INTEGRATION_TOKEN_KEY` Fernet key — only needed when integrations exit `coming_soon` (see "Up Next" below)

### Smoke-test checklist (post-deploy, needs a real user)
- [ ] Sign up via Clerk → confirm user row created in DB
- [ ] Create project → verify pathway auto-detected from idea description
- [ ] Run full discovery → verify chips appear, sheet updates in real-time, no AI repetition
- [ ] Save Place button works
- [ ] Proceed → PathwayReview loads modules → confirm → execute
- [ ] Export transcript (copy + PDF) — both roles present in output
- [ ] Mobile: pinch-zoom disabled, viewport fills correctly, TopBar chips scroll, bottom nav doesn't overlap content on iPhone
- [ ] Hit project limit on free plan → EntitlementLimitModal appears
- [ ] Click "View Plans" → goes to pricing → Stripe checkout works → webhook updates `account_type`
- [ ] Admin panel: search a user, change their plan, confirm audit log entry appears

---

## 🚧 Up Next (Queue)

User-prioritized order for the next sessions. See [`TODO.md`](TODO.md) for the concrete actionable breakdown of each item.

0. ✅ **PUSHED 2026-05-23.** All 5 v2-overhaul + doc commits are on `origin/main` and have triggered Railway auto-deploy. **Now verify the deploy is healthy, run the 5-min smoke test, and rotate the 3 exposed webhook secrets.** (Detail in [`TODO.md`](TODO.md) `🔴 P0 — DO TODAY` block.)
1. **Unified Discovery overhaul Phases 5-6** — Phases 1-4 + audit closure all shipped today. Remaining:
   - **Phase 5:** new `/design-kit/{projectId}` page with Edit + Refresh per module + Add Modules button. Includes new backend endpoints `PATCH /modules/{pid}/{mid}/responses` and `POST /modules/{pid}/{mid}/refresh-output`. Recommended sequence: Vitest scaffold + first frontend tests → Design Kit page shell + Edit + PATCH endpoint → Proceed destination swap + Library resume update → Refresh + Add Modules polish. (Full breakdown in [`TODO.md`](TODO.md) Phase 5 section.)
   - **Phase 6:** Additional discovery flow for newly-added modules (mini unified-Discovery scoped to just newly-added unfilled fields)
2. **Vitest frontend test scaffold** — currently zero frontend tests; should land EARLY in Phase 5 work so subsequent forms/optimistic-updates/refresh-affordances are testable. First tests: `useSSE` field_update parsing, `ProgressPanel` rendering + FIFO cap, `Discovery` flow_version branching, `extractError`.
3. **Notion integration** — first integration to exit `coming_soon`. Push design sheet + blocks + pipeline to a Notion page hierarchy. OAuth infrastructure + Fernet token storage already in place.
4. _(open — pick from Medium-Term Features below)_

---

## 🎯 Short-Term Polish (Backlog)

The toast migration + fetchPathway wraps are done. Remaining polish items:

### UX
- **Empty-state illustrations** on Blocks / Pipeline / PromptKit when no data exists yet
- **Keyboard shortcuts** — Cmd+K command palette for navigating between project sections
- **Sidebar inbox badge animation** — pulse on count increase

### Code organization
- **Hoist `_partnerCache`** to `frontend/src/lib/partnerCache.ts` (currently duplicated in Home.tsx + Inbox.tsx)
- **Centralize the optimistic-update pattern** used by inboxStore for future stores (toggle adjust + reconcile)
- **`inbox.py` lazy import** — `validate_partner_style` is imported inside `promote_to_project`. Move to module-level (no circular import risk).

### Performance
- **Lazy-load reactflow CSS** alongside the PitchMode bundle (currently included in the lazy chunk; ~150KB total)
- **Module-pathway store** doesn't memoize selectors — components re-render on every `loading` change even when only `pathway` is needed

### Tests
- **Backend tests for the auth refactor** — `_idempotent_create_user` + `_link_existing_email_user`. Test the 4 race scenarios end-to-end with the INSERT ON CONFLICT path
- **Backend tests for admin endpoints** — `require_admin` rejection, `update_user_plan` audit trail, `update_user_admin_flag` self-revoke block, entitlement override merge logic
- **Frontend test scaffolding** — Vitest + first tests (`extractError`, `inboxStore.adjust(-1)` clamping, `useSSE` safety-net, `adminStore` mutations)

---

## 🎁 Medium-Term Features (Next 5-10 sessions)

### Discovery experience
- **Voice transcript export** — capture full voice input as part of transcript metadata
- **AI partner mid-session preview** — show what the next AI response would look like in each partner's voice before switching
- **Discovery progress bar** — visualize stage progression more prominently than the side stepper

### Modular pathway
- **Module dependencies / prerequisites** — currently any order is valid. Add optional `requires` field to module definitions
- **Cross-module reference UI** — when AI mentions a field already answered, highlight which module/answer it's coming from
- **Module library expansion** — currently 47 modules across 7 groups. Expand to 70-100 to cover more pathways
- **Pathway templates** — save a custom pathway configuration and reuse for similar future projects
- **Re-runnable categorize/assemble** — currently fires once on PathwayReview mount; let users re-trigger after adding more discovery detail

### Sharing & collaboration
- **Realtime collaborative editing on shared projects** — partner reviews while owner iterates
- **Email digest of share comments** — daily digest of new comments/ratings
- **Public showcase** — opt-in gallery of completed projects (with owner approval)

### Integrations (currently de-scoped as `coming_soon`)
- **Notion** _(queued next — see Up Next)_ — push design sheet + blocks to a Notion page hierarchy
- **Trello / Linear** — convert MVP blocks to cards/issues
- **Figma** — generate FigJam wireframe from UI skeleton
- **Google Docs** — export Pitch document
- **Airtable** — sync block list to a base

### Billing & admin
- **Usage-based add-ons** — extra projects / AI tokens / market analyses beyond plan limits. Pairs with the entitlement-overrides system shipped today
- **Team plan** — multi-user workspaces with shared projects
- **Annual discount surfacing** — currently in code but could be more prominent
- **Admin metrics dashboard** — extend `/admin` with usage charts (signups, plan distribution, churn)

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
- **Migrate from `datetime.utcnow()`** — mostly done; audit one more pass to catch any new usage
- **SQLite test fixtures** — `conftest.py` has JSONB/UUID compat shims. Replace with PostgreSQL testcontainers for higher fidelity
- **Anthropic SDK pinning** — currently uses untyped Anthropic calls in some places. Migrate to typed `messages.create()` everywhere
- **Reduce N+1 queries** in `library.py` `_compute_resume_path` — currently issues one query per project. Add eager loading
- **Orphan user row cleanup** — one row exists with `is_admin = TRUE` but no `clerk_user_id` from the 2026-05-23 debug. Safe to leave or delete

### Frontend
- **Replace `react-router-dom` with TanStack Router** — when/if we want type-safe routing
- **Migrate ReactFlow to lazy chunk** if PitchMode bundle size becomes an issue
- **Add ESLint rule to forbid `console.error`** for user-facing failures — should always be `toast.error()`
- **Add ESLint rule to forbid `h-screen` in pages** — should be `.h-dvh` for mobile compatibility
- **Storybook** for the design system components (Button, Card, Badge, Modal, etc.)

### Infrastructure
- **Sentry / error tracking** — currently relies on Railway logs
- **Performance monitoring** — backend latency, AI call duration, p99 response times
- **Database query observability** — slow query log
- **Backup automation** — Railway has snapshots but no automated weekly export

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
- **Admin actions per week** — frequency of comps + override edits via `/admin/audit-log`

---

## ❓ Open Product Questions

1. **Should the AI partner be visible to viewers on shared projects?** Currently hidden — but partner style affects the design output, so it's relevant context.
2. **Should we support multiple AI partners per project?** Currently one per session, switchable mid-flow. Could one project have separate partners per module?
3. **Should categorize/assemble be re-runnable?** Currently fires once on PathwayReview mount. If user adds significant detail after, they can't re-trigger. _(Now listed in Medium-Term Features → Modular pathway)_
4. **Mobile-first redesign?** Current design is desktop-first with mobile responsive. Worth a full mobile-first pass given voice + email-to-inbox flows are mobile-friendly.
5. **Free tier limits**: 3 projects feels tight. Should we expand to 5 with a "lite" feature set (e.g. no market analysis on free)? _(Now potentially answered by entitlement overrides — could expand on a per-user basis instead)_
6. **Realtime inbox transport** — WebSocket vs SSE? Project already uses SSE for Discovery + Modules + Market, so SSE is the obvious choice. Decision punted to the implementation session.
