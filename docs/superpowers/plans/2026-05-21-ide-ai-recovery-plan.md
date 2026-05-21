# Ide/AI Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore Ide/AI's durable project workflow by fixing discovery resume, broken library actions, route mismatches, and high-risk authorization gaps.

**Architecture:** Execute the detailed markdown package in `docs/claude-code-package/2026-05-21-codebase-audit/` in priority order. Keep changes vertical and testable.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL, React, TypeScript, Vite, Clerk, Stripe.

---

## Plan Index

- [ ] Read `docs/claude-code-package/2026-05-21-codebase-audit/README.md`.
- [ ] Read `docs/claude-code-package/2026-05-21-codebase-audit/01-product-intent.md`.
- [ ] Read `docs/claude-code-package/2026-05-21-codebase-audit/02-current-state-audit.md`.
- [ ] Read `docs/claude-code-package/2026-05-21-codebase-audit/03-priority-roadmap.md`.
- [ ] Implement `docs/claude-code-package/2026-05-21-codebase-audit/04-plan-discovery-resume-autosave.md`.
- [ ] Implement P0 items from `docs/claude-code-package/2026-05-21-codebase-audit/05-plan-library-sharing-branching.md`.
- [ ] Implement P0/P1 items from `docs/claude-code-package/2026-05-21-codebase-audit/06-plan-security-hardening.md`.
- [ ] Continue with `docs/claude-code-package/2026-05-21-codebase-audit/07-plan-product-completion.md`.

## First Command

```powershell
git status --short
```

Expected: review existing untracked/modified files before editing.

## Verification Commands

Frontend:

```powershell
cd frontend
npm.cmd run build
npm.cmd audit
```

Backend syntax fallback:

```powershell
cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python -m compileall app -q
```

Backend tests, once dependencies are installed:

```powershell
cd backend
python -m pytest tests -q
```

