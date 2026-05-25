# Ide/AI — Memory

> Long-term context that Claude Code sessions should remember.
> Read after CLAUDE.md on every session start.
> Cross-references: [`CONTEXT_HANDOFF.md`](CONTEXT_HANDOFF.md) for current-session state, [`TODO.md`](TODO.md) for next actions, [`CHANGELOG.md`](CHANGELOG.md) for change history.
> **Last updated:** 2026-05-23

---

## Critical session-start checklist

1. ✅ Read `CLAUDE.md` first (rules + project identity + features)
2. ✅ Read `CONTEXT_HANDOFF.md` (latest session state, what just happened, what's open)
3. ✅ Read `TODO.md` (what to work on next, ordered by priority)
4. ✅ Glance at `ROADMAP.md` if user asks about future direction
5. ✅ Working directory is `C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\` — NEVER `D:\`
6. ✅ This is Windows — use `npm.cmd` not `npm`, use `python` not `python3`

---

## Conventions the user expects (learned over time)

### Process
- **No preview verification** — Do NOT start dev servers or take screenshots to verify code changes. The user handles testing manually.
- **Verification by 2 agents** — When the user says "verify with 2 agents" or "agents in parallel", spawn one edge-case verifier and one integration verifier. Re-verify after addressing findings.
- **Type-check after every frontend change** — `cd frontend && npx.cmd tsc -b --noEmit`. Backend: `python -c "import ast; ast.parse(open('path').read()); print('OK')"`.
- **Commit and push after each batch of related work** — Don't accumulate uncommitted changes. Use conventional commit format.
- **Always update handoff docs at the end of long sessions** — User explicitly asks for this when starting a new session.

### Communication
- **Be concise** — User wants summaries, not transcripts. Tables and bullet points beat prose.
- **Show what changed, what's verified, what remains** — Every multi-step task ends with this triad.
- **Use ✅ / ⚠️ / ❌ for status** — User scans these quickly.
- **Cite file:line for findings** — Never vague references.

### Code style
- **TypeScript strict mode** — Frontend uses strict TypeScript. Use proper types, never `any` unless absolutely necessary (and document why).
- **Zustand for state** — Don't introduce Redux/Jotai. Match the existing pattern (`create<State>((set, get) => ({...}))`).
- **Tailwind v4 CSS-based config** — No `tailwind.config.js`. Custom utilities go in `globals.css` outside `@layer`/`@theme` blocks.
- **No class components** — Hooks only.
- **All API routes use `/api/v1`** prefix.
- **All DB models use UUID primary keys**.
- **Default `ai_partner_style` is `"strategist"`** everywhere (model, schema, frontend init).

---

## Architecture mental model

### Request flow (auth → API → DB)
1. Browser sends `Authorization: Bearer <Clerk JWT>`
2. `apiClient.ts` (frontend) attaches token via Clerk's `getToken()`
3. FastAPI dependency `get_current_user` verifies JWT via JWKS, resolves/creates user row via INSERT ON CONFLICT
4. Router handler runs with `current_user: User` in scope
5. SQLAlchemy AsyncSession (transactional, autocommit on dependency exit)

### SSE flow (Discovery chat)
1. Client POST to `/discovery/{id}/init` or `/message`
2. Backend yields `{"type": "token", "content": "..."}` events as Claude streams
3. After stream completes: try to save assistant msg, try sheet extraction, commit
4. **Always emit `sheet_update` BEFORE `done`** (so clients that close on done still get sheet)
5. Client `useSSE` hook dispatches to `onToken` / `onSheetUpdate` / `onDone`

### Pathway flow
1. User completes Discovery → confidence ≥ 70 → "Proceed to Design Kit Pathway"
2. PathwayReview mounts → `fetchPathway` (404 = expected, fresh project)
3. `categorize` (Claude call, fallback to keyword if AI fails) → returns primary/secondary categories
4. `assemble` → returns module list based on category
5. User reviews, reorders, toggles lite/deep → Confirm
6. `updatePathway` → `lockPathway` → navigate to `/pathway-execute/{id}`
7. Module-by-module Claude conversations with `[MODULE_COMPLETE]` and `[CHIPS:]` markers

---

## Common pitfalls (lessons from past mistakes)

### Backend
- **Don't use `owner_id`** — the User FK is always called `user_id` (some tables use `created_by` for shares/branches).
- **Don't forget `await db.flush()`** before reading from a freshly-added ORM object — AsyncSession needs it.
- **JSONB columns need explicit `dict(...)` copying** when mutating — `sheet.fields_data["x"] = ...` won't trigger SQLAlchemy dirty tracking.
- **`datetime.utcnow()` is deprecated** — use `datetime.now(timezone.utc)`.
- **Migration child-table names must match `__tablename__` exactly** — not the model class name. Always grep the model first.
- **SSE generators must emit `done` ALWAYS** — wrap risky steps (commit, extraction) in try/except so the generator continues to `yield`.

### Frontend
- **`h-screen` (100vh) breaks on iOS Safari** — use `.h-dvh` utility (100dvh with vh fallback).
- **`pb-14` ignores iPhone home indicator** — use `.pb-mobile-nav` utility (includes safe-area-inset).
- **Axios default `responseType` is `'json'`** — for text/markdown responses, explicitly set `responseType: 'text'`.
- **Zustand store actions are stable references** — safe to include in `useEffect` deps without infinite loops.
- **Don't mutate Zustand state directly** — always use `set((s) => ({...}))` callback form for atomic updates.
- **React Hot Toast uses portals + high z-index** — already wired globally in `App.tsx`. Just `import toast from 'react-hot-toast'` and call `toast.error(msg)` or `toast.success(msg)`.
- **Sidebar is wrapped in ProtectedRoute everywhere except public pages** — safe to assume Clerk session exists in components mounted under it.

### Auth / race conditions
- **Clerk webhooks can arrive BEFORE the user's first JWT request** OR AFTER. Both orderings must work.
- **User table has 4 unique constraints**: `email`, `clerk_user_id`, `stripe_customer_id`, `inbox_email`. INSERT ON CONFLICT can only handle one constraint at a time.
- **The auth flow currently uses INSERT ON CONFLICT (clerk_user_id) + email-link helper** — handles both webhook-first and JWT-first races.

---

## File reference (where to look for what)

| Need | File |
|------|------|
| Add a new API route | `backend/app/routers/<domain>.py`, register in `main.py` |
| Add a new DB column | New migration in `backend/app/alembic/versions/` + model field |
| Add a new entitlement gate | `backend/app/services/entitlement_service.py` |
| Add a new partner style | `backend/app/services/partner_style_service.py` (PARTNER_METADATA + VALID_PARTNER_STYLES + fragment function) |
| Add a new pathway | `backend/app/pathways/<id>.py`, register in `pathways/__init__.py` |
| Add a new module to library | `backend/app/data/module_library.seed.json` |
| Add a new template | `project_templates.seed.json` |
| Add a new modal | `frontend/src/components/ui/` |
| Add a new Zustand store | `frontend/src/stores/<name>Store.ts` (match inboxStore.ts pattern) |
| Show a toast | `import toast from 'react-hot-toast'; toast.error(msg)` |
| Add a new page | `frontend/src/pages/`, register in `App.tsx` ROUTE_SUFFIX_MAP if project-scoped |

---

## Things explicitly de-scoped (don't try to add these)

- **Custom JWT auth** — Clerk handles all of this. The old jwt-auth code is gone.
- **Email/password reset flows** — Clerk handles this. `password_resets` table exists from old code but is unused.
- **Integrations (Notion, Trello, etc.)** — infrastructure exists but providers return `status: "coming_soon"`. Don't wire them up without explicit user request.
- **Server-side rendering** — Vite SPA only. No SSR.
- **Multi-tenancy** — single user per project. No teams (yet).
- **Native mobile** — web-only. PWA-friendly but not installed.

---

## Quick command reference

```bash
# Type-check frontend (after any frontend change)
cd "C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\frontend" && npx.cmd tsc -b --noEmit

# Validate Python syntax (after any backend change)
cd "C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\backend" && python -c "import ast; ast.parse(open('app/routers/auth.py').read()); print('OK')"

# Run backend tests
cd "C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\backend" && python -m pytest tests/ -v

# Git status + recent commits
cd "C:\Users\vybec\OneDrive\Documents\Development\Ide_AI" && git status --short && git log --oneline -5

# Install a new frontend dep
cd "C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\frontend" && npm.cmd install <pkg> --save

# Install a new backend dep
cd "C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\backend" && pip install <pkg> && pip freeze > requirements.txt
```

---

## Most recent session signature (what to expect when resuming)

- **Date:** 2026-05-23 (end-of-day marathon session — Phases 1-4 of v2 overhaul shipped + pushed)
- **HEAD:** `(latest doc-update commit — check git log)` — last v2 work commit is `585cb7d`
- **Remote:** `origin/main` is in sync with local `main` as of 2026-05-23 end-of-session push. **All 5 v2-overhaul + doc commits are pushed to GitHub and have triggered Railway auto-deploy.**
- **Branch:** `main` (working tree clean except long-standing untracked AGENTS.md and docs/claude-code-package/2026-05-21-post-update-audit/)
- **Last commits (in order, oldest first — all PUSHED):**
  1. `a7257e0` — Phase 3 hotfix (5 audit-found bugs + doc sweep)
  2. `b26837a` — Phase 4 features (ProgressPanel + v2 Discovery wiring + module-preview a11y)
  3. `ff212f3` — Phase 4 audit closure (15 findings + 35 unit tests)
  4. `57aa9d3` — HTTP integration tests + H1 greenlet bug fix (real production bug)
  5. `f8d3165` — Doc lockdown (P0 block + sequencing + regression matrix)
  6. `585cb7d` — Doc unification (closed staleness drift + cross-reference gaps)
- **State:** Phases 1-4 + audit closure + integration tests + all docs ALL shipped and pushed. 91/91 backend tests pass. TypeScript build clean. Discovery v2 fully functional end-to-end on the frontend. Railway auto-deploy triggered on push.
- **Next:**
  1. **P0 (now reduced):** verify Railway deploy succeeded (both services healthy), run 5-min smoke test on https://myide.ai, rotate the 3 exposed webhook secrets. See TODO.md `🔴 P0 — DO TODAY`.
  2. **Phase 5:** Design Kit page at `/design-kit/{projectId}` — see TODO.md Phase 5 (numbered 7 items with recommended sequencing) and CONTEXT_HANDOFF.md for the full picture. Recommended order: Vitest scaffold → DesignKit page shell + Edit + PATCH endpoint → Proceed destination swap + Library resume routing → Refresh + Add Modules polish.
  3. **Phase 6:** Additional Discovery for newly-added modules
- **Key files added this session:**
  - `frontend/src/components/discovery/ProgressPanel.tsx`
  - `backend/tests/test_discovery_v2.py` (35 service-layer tests)
  - `backend/tests/test_discovery_v2_integration.py` (15 HTTP-route tests)
  - Project memory: `discovery-v2-architecture.md` (auto-loaded; reflects Phases 1-4 shipped + pushed state)
