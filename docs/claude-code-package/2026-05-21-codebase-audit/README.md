# Ide/AI Codebase Audit Package

Date: 2026-05-21

This package is written for a follow-on Claude Code development session. It separates:

- what Ide/AI is trying to achieve,
- where the current codebase stands,
- what must be fixed or built next,
- how to execute the highest-priority changes safely.

## Recommended Reading Order

1. `01-product-intent.md` - product description and target user journey.
2. `02-current-state-audit.md` - current implementation status and evidence.
3. `03-priority-roadmap.md` - ordered remediation roadmap.
4. `04-plan-discovery-resume-autosave.md` - P0 implementation plan for the discovery progress loss bug.
5. `05-plan-library-sharing-branching.md` - library, sharing, inbox, and branching fixes.
6. `06-plan-security-hardening.md` - targeted security and dependency fixes.
7. `07-plan-product-completion.md` - remaining product work to reach the intended Ide/AI experience.
8. `08-claude-code-master-prompt.md` - copy-paste handoff prompt for Claude Code.
9. `09-verification-log.md` - local verification results from this audit.

## Executive Summary

Ide/AI is intended to be a pre-builder planning platform: users describe a rough idea, collaborate with an AI partner through discovery, produce a structured design sheet, generate a modular design kit pathway, and export builder-ready artifacts for tools such as Claude Code, Cursor, Bolt, Replit, and related builder environments.

The codebase has a substantial implemented skeleton: FastAPI routers, Clerk auth, Stripe billing, SSE discovery, pathway registries, module pathway assembly, project templates, exports, market analysis, sprint planning, and a React/Vite frontend. The frontend currently builds successfully after installing dependencies.

The strongest product risk is not absence of features; it is incomplete wiring between features. Several advertised flows exist partially but are not resume-safe, have route mismatches, or do not persist enough state to support the intended "15-30 minute planning workspace" model.

The user-reported library/discovery issue is confirmed:

- `frontend/src/pages/Discovery.tsx` calls `POST /discovery/start` on every mount.
- `backend/app/routers/discovery.py` routes that request to `discovery_service.create_session`.
- `backend/app/services/discovery_service.py` always creates a new `DiscoverySession`.
- The old session may still exist in the database, but the UI abandons it and starts a fresh greeting.

The fix is to make discovery start/resume idempotent, load saved sheet state on entry, and add tests around resumability.

## Important Constraints For Claude Code

- Do not use `D:\Development\ideaFORGE`. Work only in this repo checkout.
- Do not start local dev servers or browser previews. The project AGENTS.md says manual preview is handled by the user.
- Use `npm.cmd` on Windows PowerShell for npm commands.
- If building locally after dependency install, `npm.cmd run build` currently passes.
- Backend pytest could not be run in this environment because `pytest` and backend runtime dependencies were not installed.
- CodeRabbit CLI was not available and could not be installed in this shell because `sh` is missing. Do not claim CodeRabbit review results.

