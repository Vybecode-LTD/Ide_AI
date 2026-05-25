# C. Priority Findings And Roadmap

This file orders the work by user impact and risk.

## P0: Fix Discovery Autosave So It Cannot Delete Progress

### Finding

`frontend/src/pages/Discovery.tsx` added autosave on unmount, visibility change, interval, and stage change. The unmount effect depends on `saveProgress`, and `saveProgress` depends on `messages` and `stage`. That means the cleanup runs not only on true unmount, but also whenever messages or stage change.

The cleanup can send stale messages to:

`PATCH /discovery/{session_id}/progress`

The backend then replaces canonical session messages:

```python
session.messages = payload.messages
session.stage = payload.stage
```

### Impact

This can erase newly persisted user or assistant messages. The original discovery progress issue is improved, but this implementation can still lose progress through stale client state.

### Required Outcome

- The client must not overwrite backend messages with stale arrays.
- Progress save must be monotonic or merge-aware.
- Backend should remain the canonical owner of sent messages.

## P0: Recover Projects Affected By The Old Empty-Session Bug

### Finding

`get_latest_active_session_for_project` returns the latest active session. For users who hit the old bug, the latest active session may be an empty session created after the real session.

### Impact

Those users still see empty discovery even though their older non-empty session exists.

### Required Outcome

- Resume should prefer a non-empty active session over a newer empty active session.
- Add a one-time cleanup/migration or runtime fallback to retire empty orphan sessions when a non-empty session exists.

## P0: Make Library Resume Path Match Real Project State

### Finding

`_compute_resume_path` routes active sessions to Discovery. Discovery sessions are never marked complete. Therefore a project that reached `confirm` can still route back to Discovery instead of Pathway Review.

### Impact

Library still fails its core role as the reliable resume surface.

### Required Outcome

- Decide whether discovery completion is represented by `session.status`, `session.stage`, or both.
- Make backend and frontend use the same completion semantics.
- Ensure a confirmed discovery routes to `/pathway-review/{projectId}`.

## P0: Persist Module Pathway Completion

### Finding

Modules can be complete or skipped, but `ModulePathway.status` is not updated to `complete`.

### Impact

Library and execution hub can get stuck showing "Modules in progress." The frontend completion calculation is also race-prone.

### Required Outcome

- Backend updates `ModulePathway.status = "complete"` when every module is complete or skipped.
- Frontend recomputes completion after either pathway or responses load.

## P1: Replace Resend HMAC With Svix Verification

### Finding

The inbound email webhook computes a bare HMAC digest. Resend documents Svix verification using `svix-id`, `svix-timestamp`, and `svix-signature`.

### Impact

Production webhook delivery can fail, and replay protection is not active.

### Required Outcome

- Use `svix.Webhook(settings.RESEND_WEBHOOK_SECRET).verify(raw_body, headers)`.
- Preserve raw body.
- Add idempotency using `svix-id`.
- Return proper 4xx status for invalid/oversized payloads.

## P1: Protect Feedback Endpoints For Password-Protected Shares

### Finding

Main shared project data requires password when configured, but comments and ratings only require the token.

### Impact

Password-protected shares still expose feedback metadata and allow unauthenticated posting.

### Required Outcome

- Add viewer access proof after password verification.
- Require that proof for comments, ratings, and CSV on private shares.
- Keep public shares simple.

## P1: Make Entitlements Consistent And Count-Based

### Finding

Only `POST /projects`, prompt generation, and market generation are gated. Template use, inbox promotion, branch creation, and `.ideai` import bypass project limits. Count-limited paid features are not actually counted.

### Impact

Billing limits can be bypassed, and paid plans are not enforced as described.

### Required Outcome

- Centralize project creation gates.
- Gate every project creation path.
- Count prompt kits, market analyses, and sprint plans.
- Add frontend upgrade handling for 403 responses.

## P1: Fix Lint Failures

### Finding

`npm.cmd run lint` fails with 12 errors and 7 warnings.

### Impact

The codebase has correctness and maintainability issues that TypeScript build does not catch.

### Required Outcome

- Make lint pass.
- Treat hook dependency and stale closure findings as correctness work, not style cleanup.

## P1: Make Backend Tests Runnable

### Finding

The new discovery tests require fixtures that do not exist. Local Python also lacks backend dependencies, so test execution could not be verified.

### Impact

The highest-risk fixes have no executable regression suite.

### Required Outcome

- Add `backend/tests/conftest.py`.
- Provide async database fixtures or mark tests explicitly skipped until a test database is configured.
- Add tests for stale auto-save prevention, empty-session recovery, library resume path, and pathway completion.

## P2: Complete Branching Semantics

### Finding

Branch deep copy exists but omits several artifacts and fields. Merge deletes parent market analysis and does not restore branch market analysis.

### Impact

Branching can silently drop user work.

### Required Outcome

- Copy all state gathered by `_gather_project_state`.
- Preserve `fields_data`, `ai_partner_style`, `completed_at`, and market analysis.
- Add tests for branch, compare, and merge.
- Add frontend UI or remove claims that compare/merge are user-facing.

## P2: Update Docs And Environment Files

### Finding

The repo now has multiple sources of truth: `AGENTS.md`, `CLAUDE.md`, `CONTEXT_HANDOFF.md`, `README.md`, `env.example`, and `frontend/README.md`. They conflict.

### Impact

Future agents and deployments can use wrong env vars or stale architecture assumptions.

### Required Outcome

- Align all docs on React 19, Claude model naming, migration 024, current stores, current routes, and env vars.
- Replace frontend template README.
- Add security env vars to `env.example`.
- Use `ANTHROPIC_KEY` consistently or add backwards-compatible alias support.

## Recommended Execution Order

1. Discovery autosave and empty-session recovery.
2. Library resume and pathway completion.
3. Security fixes for Resend and private share feedback.
4. Entitlement consistency.
5. Lint cleanup.
6. Test fixtures and regression coverage.
7. Branching completeness.
8. Docs/env cleanup.

