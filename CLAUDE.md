# CLAUDE.md — Ide/AI

> **Version:** 3.5.0 · **Last updated:** 2026-11-25 · See [CHANGELOG.md](CHANGELOG.md)

## Identity
Ide/AI (`myide.ai`, formerly ideaFORGE) turns a rough idea into an export-ready design kit (features,
stack recommendation, platform prompts, documentation) through an AI-guided discovery chat, before the
user spends credits in a metered builder. Stack: FastAPI on Python 3.12 (async SQLAlchemy, Alembic,
PostgreSQL, Claude), React 19 + TypeScript + Vite 7 + Tailwind v4, Clerk auth, Stripe, Resend. Repo
`github.com/Vybecode-LTD/Ide_AI`, branch `main`. A web app on Railway: backend and frontend, both public,
and **a push to `main` deploys both.**

## Current State
- **Phase:** back in work after five idle months. A full audit ran on 2026-11-23; its report is
  `dev plans/project-assessment-2026-11-23.md`, kept out of git because **this repository is public**.
  It stays public, deliberately open source (owner, 2026-11-24).
- **Live:** pull requests #1 to #4, all merged and deployed (`main` at `b6c966a`). Merged and deployed on
  2026-11-24 were module session start, edits persisting and the Exports limit error (#1), module saves made
  during a model call (#2), and length caps on chat messages and descriptions (#3). Audit step 2 (#4) went
  live on 2026-11-25 at 03:44 UTC (22:44 ET on the 24th): dependency updates, the backup job in
  `ops/db-backup/`, the new CI and scrubbed error tracking. The #4 deploy was checked: both services
  SUCCESS, the Frontend built on Node 24, health 200, and the live CSP allows Sentry. No signed-in user
  has confirmed #1 to #3 on myide.ai yet.
- **Not running yet:** backups (no `db-backup` service in Railway) and error tracking (no DSNs). Both wait
  on the owner's setup steps: TODO.md, top.
- **Waiting on the owner:** the checks and decisions in section 6 of the audit report, the setup steps
  above, and a ruleset on `main` requiring "CI result".
- **CI:** `.github/workflows/ci.yml`, one gate, the "CI result" check; it passed on #4. Nothing requires it
  yet (no ruleset). The old workflows are deleted (`test-pipeline.yml`, `db-backup.yml`); `uptime-check.yml`
  is still disabled.

Next steps, blockers and warnings live in CONTEXT_HANDOFF.md and TODO.md, this project's equivalents of
docs/HANDOFF.md.

## Commands
| What | Where | Command |
|---|---|---|
| Backend tests | `backend` | `poetry run python -m pytest` |
| Migrations | `backend` | `alembic upgrade head` |
| Backend dependency audit | `backend` | `poetry export -f requirements.txt --all-extras --without-hashes -o req.txt && pip-audit -r req.txt --disable-pip --no-deps` (CI's command; without `--all-extras` it skips pytest and the other dev tools) |
| Frontend type-check (after every change) | `frontend` | `npx.cmd tsc -b --noEmit` |
| Frontend tests | `frontend` | `npx.cmd vitest run` |
| Frontend build, with prerender | `frontend` | `npm.cmd run build` |
| Backup job tests | `ops/db-backup` | `python -m pytest` (setup and restore drill: its `README.md`) |

## Architecture (brief)
- **Flow:** idea → options → AI discovery chat (partner style shapes *how* it asks) → structured extraction →
  design sheet, blocks board, pipeline, prompt kit, market analysis, sprint plan, pitch → export (PDF, DOCX,
  ZIP).
- **Backend:** FastAPI under `/api/v1`, async SQLAlchemy models with UUID keys, a linear Alembic chain, and
  Claude streamed over SSE for discovery, market analysis and module responses.
- **Frontend:** React hooks only, Zustand for local state, React Query for server state; Tailwind v4 is
  configured in CSS (no `tailwind.config.js`).
- **Auth and billing:** Clerk (OAuth and email), Stripe checkout, portal and webhook entitlements.
- **Integrations:** Notion live (3-legged OAuth); Resend inbound email feeds the Idea Inbox.
- Full detail: ARCHITECTURE.md (structure, stack, design system, migrations, API routes, known issues).

## Critical Gotchas
1. **Each AI partner must genuinely behave like its namesake,** and partner choice never changes the
   structured output schema. The default partner is `"strategist"` everywhere.
2. **All routes are prefixed `/api/v1`; every model uses a UUID primary key.**
3. **Push to `main` deploys both services.** Merging to `main` is the owner's call.
4. **No preview verification:** don't start dev servers or take screenshots; the owner tests by hand.
5. **The frontend CSP (`frontend/Caddyfile`) must allow `https://clerk.myide.ai` and the backend origin
   without a path,** or the SPA white-screens or every API call is blocked (ARCHITECTURE.md, Known Issues).
6. **Integration tests in `test_partner_style.py` need the `anthropic` module;** run backend tests in the
   poetry environment.
7. **Windows:** use `npm.cmd`/`npx.cmd`, and `python`, not `python3`.

## Conventions
- **Documentation follows DOC_VERSIONING.md,** which overrides the generic kit: root-level docs, SemVer per
  doc, one root CHANGELOG.md, and a Stop hook that nags when code ships without a CHANGELOG entry. Never
  create a `docs/` managed-doc tree. The end-of-session checklist is in WORKFLOW.md.
- **The working directory is `C:\DEV\Ide_AI`.** Older docs name `C:\Users\vybec\OneDrive\Documents\
  Development\Ide_AI\` or `D:\Development\...`: those are obsolete, and nothing may be written into OneDrive.
- Conventional commits; confirm with `git status` and `git log` before saying anything is pushed.
- **Sections moved on 2026-10-15,** headings unchanged: What This Software Does, Tech Stack, Project
  Structure, Design System, Database Migrations, API Routes and Known Issues → ARCHITECTURE.md (appended at
  the end); Features → FEATURES.md; Project Identity, Documentation Discipline, Binding Directives, Critical
  Rules, Git Workflow, Session Recovery, Documentation and Last Completed Task → WORKFLOW.md. The whole
  previous file: docs/archive/CLAUDE.pre-lean-2026-10-15.md.

## Project Map
| Topic | File | Read this when... |
|---|---|---|
| Latest session state, what shipped, what's open | CONTEXT_HANDOFF.md | starting a session or picking up work |
| Next steps, by priority | TODO.md | deciding what's next |
| Doc versioning convention | DOC_VERSIONING.md | committing anything that touches docs |
| Conventions, pitfalls, mental model | MEMORY.md | before a first change in an area |
| Architecture, stack, structure, migrations, API routes, known issues | ARCHITECTURE.md | changing structure, adding a route, model or migration |
| Feature inventory (27 features) | FEATURES.md | checking whether something already exists |
| Workflow, documentation checklist, binding directives, critical rules, last completed task | WORKFLOW.md | before a commit, or when a rule seems to apply |
| Changelog | CHANGELOG.md | needing recent history of a change |
| Roadmap | ROADMAP.md | discussing forward direction |
| Railway deployment | DEPLOYMENT_RAILWAY.md | wiring services or variables |
| Product and specs | PRD.md, FEATURE_SPEC.md, AI_PARTNER_SELECTOR_SPEC.md, MODULAR_PATHWAY_SPEC.md | designing a feature |
| Audit packages | docs/claude-code-package/ | reading an audit |
| Deep history | docs/archive/ | needing older context |

## Process references
The directive manuals are vendored at the repo root. They're no longer `@include`d (that loaded about
40 KB every session); read each by path when its trigger applies. Where one conflicts with this file, this
file wins.
- `DEBUG_PROTOCOL.md`: read when a second fix for the same symptom fails.
- `TESTING_PROCEDURES.md`: read when adding test infrastructure. Active stacks: Python/FastAPI and
  React/Vite only; its dev-server and browser steps yield to Critical Gotcha 4.
- `VERSION_CONTROL.md`: read before rewriting history or cleaning up a secret.
- `SEO_OPTIMIZATION.md`: read before changing a public myide.ai page (`seo-research-catalog.md` is the deep reference).
- `SOFTWARE_RELEASE.md`: not applicable (a web app).
