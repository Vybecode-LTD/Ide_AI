# Workflow, rules and session state: Ide/AI

> Moved verbatim from `CLAUDE.md` on 2026-10-15 (lean-context pass). Section numbers are unchanged, so a citation such as `CLAUDE.md §5a` is found here by its heading.

> Moved from `CLAUDE.md` on 2026-10-15.

## Project Identity

- **Name:** Ide/AI (codebase directory: `Ide_AI`, formerly known as ideaFORGE)
- **Repo:** `github.com/Vybecode-LTD/Ide_AI`
- **Working directory:** `C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\` — this is the ONLY working directory for this codebase. Any references in older docs to `D:\Development\Ide_AI\` or `D:\Development\ideaFORGE\` are obsolete.
- **Branch:** `main`
- **Deployment:** Railway (2 public services: backend + frontend, no reverse proxy)

---

> Moved from `CLAUDE.md` on 2026-10-15.

## Documentation Discipline

**This project versions its documentation.** Read [DOC_VERSIONING.md](DOC_VERSIONING.md) for the full convention. The TL;DR for every code-touching session:

### Doc system scope — this project overrides the generic Claude-Kit

[DOC_VERSIONING.md](DOC_VERSIONING.md) is the **binding** documentation convention for Ide/AI: **root-level docs, SemVer _per doc_, one root [CHANGELOG.md](CHANGELOG.md), and the Stop hook.**

The parent `Development/CLAUDE.md` "Project Constitution" `@include`s a generic `DOCUMENTATION_MANAGER.md` describing a *different* system — a `docs/` managed-doc tree (`docs/BUGS.md`, `docs/HANDOFF.md`, `docs/AUDIT-LOG.md`, …), one **shared** version number across all docs, and `initialize project docs`. **That generic system does NOT apply here and must not be installed.** This project already tracks the same concerns in its root docs:

| Generic kit doc | Ide/AI equivalent (root-level) |
|---|---|
| `docs/ROADMAP.md` | [ROADMAP.md](ROADMAP.md) |
| `docs/CHANGELOG.md` | [CHANGELOG.md](CHANGELOG.md) |
| `docs/HANDOFF.md` | [CONTEXT_HANDOFF.md](CONTEXT_HANDOFF.md) |
| `docs/BUGS.md` | tracked in [TODO.md](TODO.md) + CHANGELOG `Fixed` entries |
| `docs/TESTING.md` | "Regression Test Matrix" in [CONTEXT_HANDOFF.md](CONTEXT_HANDOFF.md) |
| `docs/AUDIT-LOG.md` | not used — audit packages live under `docs/claude-code-package/` |

The `session-orchestrator` skill is installed **globally** and may be used for chronicling / reconciliation, **but it must operate on the root-level docs above — never create a `docs/` managed-doc tree, never impose a single shared version, never run `initialize project docs`.** The project-local [DOCUMENTATION_MANAGER.md](DOCUMENTATION_MANAGER.md) has been reconciled to match this mapping; the generic copies under `Development/` are unchanged and remain for other projects.

### End-of-session checklist (required)

Before declaring a task complete or committing, walk through this:

1. **Touched a feature listed in CLAUDE.md?** → Update that feature's description here, bump CLAUDE.md version.
2. **Touched a backend route, model, migration, or service?** → Reflect in CLAUDE.md Database Migrations / API Routes tables.
3. **User-visible behavior changed?** → Add a CHANGELOG.md entry under `[Unreleased]` (or today's date) with Added/Changed/Fixed/Security category.
4. **Resolved a TODO item?** → Move it to "Recently Done" in TODO.md.
5. **Session-defining work shipped?** → Update CONTEXT_HANDOFF.md "Current Session" with the commit refs.
6. **Bumped any versioned doc?** → Update its `Last updated` field to today's date.

### Versioned docs (frontmatter required)

These carry a `> **Version:** X.Y.Z · **Last updated:** YYYY-MM-DD · See [CHANGELOG.md](CHANGELOG.md)` line immediately after their H1:

- CLAUDE.md (this file)
- CONTEXT_HANDOFF.md
- TODO.md
- DOC_VERSIONING.md
- (CHANGELOG.md is append-only — no version on itself)

When you bump:
- **MAJOR** (X.0.0): restructure, new top-level section, content that contradicts previous version
- **MINOR** (X.Y.0): new content in existing section, new row in a table, new feature
- **PATCH** (X.Y.Z): typo, link fix, clarification

### Enforcement

- **Stop hook** at `.claude/hooks/check-doc-versioning.sh` fires when a session ends. If the latest commit touched `frontend/src/` or `backend/app/` files but didn't touch CHANGELOG.md, it prints a warning. **Non-blocking** — just a reminder.
- If you legitimately don't need a CHANGELOG entry (pure internal refactor, no doc impact), it's fine to ignore the nag. The hook errs on the side of reminding.
- The hook lives in `.claude/settings.json` under `hooks.Stop`. Don't disable it without proposing a replacement.

---

> Moved from `CLAUDE.md` on 2026-10-15.

## Binding Directives (vendored)

The Claude-Kit directives are **vendored at the repo root** and wired in here so a fresh clone or a cloud session is self-governing — the parent `Development/` constitution is absent from a standalone checkout. They apply **in addition to** the rules in this file. **Where any directive conflicts with this file, this file wins** (it is the project-specific override). On a machine that also loads the parent constitution, these reconciled project copies are the source of truth for this repo.

@DEBUG_PROTOCOL.md
@VERSION_CONTROL.md
@TESTING_PROCEDURES.md
@SEO_OPTIMIZATION.md

Scope notes for this project:

- **Testing** (`TESTING_PROCEDURES.md`) — active stacks are **Python/FastAPI + React/Vite only** (skip the C#/Avalonia sections). Its "start the dev server / browser smoke / Playwright E2E / launch the app" steps **yield to Critical Rule #8** (no preview verification — the user tests manually); automated verification is `pytest`, `npx.cmd vitest run`, and `npx.cmd tsc -b --noEmit`.
- **Documentation** — governed by [DOC_VERSIONING.md](DOC_VERSIONING.md); the reconciled `DOCUMENTATION_MANAGER.md` is tracked for reference but **not** `@include`d (its discipline is already inline above and in DOC_VERSIONING.md).
- **SEO/GEO** (`SEO_OPTIMIZATION.md`) — applies to the public **myide.ai** pages; the 200-technique `seo-research-catalog.md` is a deep reference, loaded on demand (not inlined).
- **Software release** — **N/A**: Ide/AI is a web app (Railway auto-deploy on push to `main`), not a desktop download. `SOFTWARE_RELEASE.md` is kept only as an N/A stub.

---

> Moved from `CLAUDE.md` on 2026-10-15.

## Critical Rules

1. **Each AI Partner must genuinely live up to its namesake in behavior. Not cosmetic.** Every partner fragment contains detailed behavioral instructions with Core Behaviour, Questioning Style, and Guardrails.
2. **Structured output schema is never altered by partner choice.** Partners change *how* the AI collaborates, not *what* gets extracted.
3. **All API routes are prefixed with `/api/v1`.**
4. **All DB models use UUIDs as primary keys.**
5. **Frontend: hooks only, no class components. Zustand for local state, React Query for server state.**
6. **Railway deployment: both services auto-deploy on push to `main`. No reverse proxy — backend and frontend are exposed publicly.**
7. **Partner style default is `"strategist"` everywhere (model defaults, schema defaults, frontend state init).**
8. **No preview verification required.** Do not start dev servers or take screenshots to verify code changes. The user handles testing manually.
9. **Before declaring a code-touching task complete, run the [Documentation Discipline](#documentation-discipline) checklist.** Bump affected versioned docs and add a CHANGELOG.md entry. The Stop hook will nag if you skip CHANGELOG.

---

> Moved from `CLAUDE.md` on 2026-10-15.

## Git Workflow

- When asked to push changes, ALWAYS verify with `git status` and `git log` before claiming completion.
- Never say changes are pushed without confirming via actual shell output.
- Commit messages follow conventional commits format.

---

> Moved from `CLAUDE.md` on 2026-10-15.

## Session Recovery

**Read in this order on every session start:**
1. **`CLAUDE.md`** (this file) — project identity, features, critical rules
2. **`DOC_VERSIONING.md`** — doc-versioning convention (read once, refer back when committing doc-touching work)
3. **`MEMORY.md`** — conventions, common pitfalls, architecture mental model
4. **`CONTEXT_HANDOFF.md`** — latest session state, what just shipped, what's open
5. **`TODO.md`** — concrete next steps prioritized by blocker → high → nice-to-have
6. **`CHANGELOG.md`** — what changed recently (skim the most recent dated entry to see the project's current arc)
7. **`ROADMAP.md`** — only when discussing forward direction

**Working directory:** ALWAYS `C:\Users\vybec\OneDrive\Documents\Development\Ide_AI\`. Older docs may reference `D:\Development\Ide_AI\` or `D:\Development\ideaFORGE\` — those paths are obsolete.

**Platform:** Windows. Use `npm.cmd` not `npm`, `python` not `python3`. Type-check after every frontend change: `npx.cmd tsc -b --noEmit`. Validate Python syntax via `python -c "import ast; ast.parse(open('...').read())"`.

---

> Moved from `CLAUDE.md` on 2026-10-15.

## Documentation

This project follows the [DOC_VERSIONING.md](DOC_VERSIONING.md) convention — SemVer per doc, root [CHANGELOG.md](CHANGELOG.md), manual discipline. When you ship code that changes a documented feature, bump the affected doc's version + last-updated date and add a CHANGELOG entry. See `DOC_VERSIONING.md` for the full checklist.

---

> Moved from `CLAUDE.md` on 2026-10-15.

## Last Completed Task

**Task:** Production-hardening sweep (P0→P4 from the 2026-06-10 readiness audit), on branch **`chore/production-hardening`** (4 commits, NOT yet merged/pushed — merging is the user's call since push = deploy):
- **P0 — npm CVEs:** `npm audit fix` → react-router 7.17.0 + js-cookie 3.0.7 (closes DEP-H1); `npm audit` now 0 vulns.
- **P1 — SAST-H1 + backend CVE sweep:** slowapi per-IP rate limiting (`app/core/rate_limit.py`; public sharing comments/ratings/verify 10/min, shared GET 30/min, inbound-email webhook 60/min, `/pathways/detect` 10/min; XFF-aware keying; `RATE_LIMIT_ENABLED` flag; 7 tests in `test_rate_limit.py`). `poetry update` cleared all 26 pip-audit advisories (pyjwt 2.13, starlette **1.2.1**, etc.) — lock now audits clean. Clerk JWT `leeway=30`. `/pathways/detect` description capped 5000 chars. Stripe webhook idempotency audited: idempotent by construction, no change.
- **P3 — observability:** Sentry both services (deploy-dark: no-op until DSN env set), `.github/workflows/db-backup.yml` (weekly pg_dump → 90-day artifact; needs `DATABASE_PUBLIC_URL` repo secret), `.github/workflows/uptime-check.yml` (30-min health pings).
- **P4 — hygiene:** tour auto-launch now new-signups-only (≤7-day account age); stale `AGENTS.md` deleted; 6 inbox tests (`test_inbox.py`: /inbox/count correctness + promote partner-style validation).

_Prior task (2026-05-31): shipped the Guided Tour (#26) + Blog (#27) — merged `4a15472`, deployed, migration 033. Before that: Notion integration live (`32ec540`)._

**Date:** 2026-06-10
**Test coverage:** **Backend 306 collected across 14 files — 305 passed · 1 skipped (PG-only upsert)** (run in the poetry env, where the 4 PromptComposition tests also pass). **Frontend 60/60 across 9 files**; `tsc -b --noEmit` clean, ESLint clean, **full `npm run build` green incl. prerender**; `npm audit` + `pip-audit` (locked set) both **0 vulnerabilities**.
**Residual (non-blocking, mostly user actions — see TODO.md "Needs YOUR action"):** merge + push the branch (= deploy); bootstrap an admin (Blog CMS); set `SENTRY_DSN`/`VITE_SENTRY_DSN` in Railway + `DATABASE_PUBLIC_URL` repo secret; live-verify tour/blog/Notion-push/429s; orphan user row cleanup; PG-backed test harness (the 1 perpetual skip + auth ON CONFLICT race paths); frontend component tests for DesignKit edit/save + Notion components; blog build-time prerender (Known Issue #6).
