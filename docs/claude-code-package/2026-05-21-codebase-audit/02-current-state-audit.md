# B. Current Codebase State

## Verification Snapshot

Local checks performed during this audit:

- `npm.cmd ci` in `frontend/`: passed, installed dependencies from lockfile.
- `npm.cmd run build` in `frontend/`: passed.
- `npm.cmd audit --json`: failed with audit findings, reporting 9 vulnerabilities: 1 critical, 5 high, 3 moderate.
- `python -m compileall app -q` in `backend/`: passed syntax compilation.
- `python -m pytest tests -q` in `backend/`: could not run because the default Python environment has no `pytest`.
- `from app.main import app`: could not run because backend runtime dependencies such as `fastapi` are not installed locally.
- CodeRabbit CLI: unavailable; install attempt failed because this Windows shell does not have `sh`.

## Architecture That Exists

The app has a broad two-service architecture:

- FastAPI backend in `backend/app`.
- React/Vite frontend in `frontend/src`.
- SQLAlchemy async models with Alembic migrations.
- Clerk token verification in `backend/app/core/clerk.py`.
- Stripe billing router in `backend/app/routers/billing.py`.
- SSE flows for discovery, market analysis, sprint generation, and module responses.
- Pathway registry in `backend/app/pathways`.
- Modular pathway services in `backend/app/services/modular_pathway_service.py` and `module_service.py`.
- Project templates seeded through migrations and JSON seed files.
- Export services for design kits, market analysis, transcripts, and prompt packages.

## Major Mismatch Between Docs And Code

The docs and AGENTS.md are useful but not fully current.

Examples:

- AGENTS.md says frontend stack is React 18, but `frontend/package.json` uses React 19.2.0.
- AGENTS.md says there are stores such as `discoveryStore` and `projectStore`, but the actual `frontend/src/stores` directory only contains auth, pathway, module pathway, and tutorial stores.
- CONTEXT_HANDOFF.md still lists legacy auth pages and reset-password flows that AGENTS.md says were removed.
- `ARCHITECTURE.md` still describes old store architecture.
- Several pathway base personas still say `ideaFORGE` instead of `Ide/AI`.
- `backend/app/schemas/user.py` still contains custom auth/password reset schemas even though Clerk now owns sign-in and password reset.

These doc/code mismatches matter because a future agent could implement against stale architecture.

## Confirmed P0 Bug: Discovery Progress Is Not Resumed

Evidence:

- `frontend/src/pages/Discovery.tsx:161` calls `apiClient.post('/discovery/start', { project_id: projectId })` every time the page mounts.
- `backend/app/routers/discovery.py:40` calls `discovery_service.create_session(db, payload.project_id)`.
- `backend/app/services/discovery_service.py:36` defines `create_session`.
- `backend/app/services/discovery_service.py:45` creates a new `DiscoverySession` every time.
- `backend/app/services/discovery_service.py:54-57` only reuses the design sheet if one already exists; it does not reuse the session.

The backend is saving some progress:

- User messages are appended and committed in `backend/app/routers/discovery.py:135-136`.
- Assistant messages are appended in the stream at `backend/app/routers/discovery.py:179`.
- Sheet extraction happens at `backend/app/routers/discovery.py:182`.
- There is a progress endpoint at `backend/app/routers/discovery.py:209`.

But the resume entrypoint abandons the saved session by creating a fresh one. That makes the user experience look like progress was lost from the library, even if old rows exist in the database.

Additional persistence gaps:

- Discovery only auto-saves frontend-local `messages` every 30 seconds at `frontend/src/pages/Discovery.tsx:44` and `:93-102`.
- There is no explicit save on unmount, route change, page hide, or before unload.
- The discovery page does not load the saved design sheet on entry; it only updates `sheet` when a `sheet_update` SSE event arrives.
- The `sheet_update` event is yielded after `done`; depending on stream handling or early navigation, the UI may miss the sheet update even though the database was updated.

## Library State

What exists:

- `backend/app/routers/library.py` lists projects with snapshot counts.
- `backend/app/services/library_service.py` can gather project state, export `.ideai`, import `.ideai`, create snapshots, list snapshots, and restore snapshots.
- `frontend/src/pages/Library.tsx` lists projects, supports search/sort, creates snapshots, imports/exports `.ideai`, restores snapshots, and links to discovery.

Key gaps:

- Library project rows do not show discovery progress, confidence score, active session, module pathway status, block count, export readiness, or last active workflow step.
- Opening a project always links to `/discovery/:projectId`; it does not choose the correct resume route based on project state.
- Snapshots and versions are duplicated concepts: `project_snapshots` powers Library, while `versions` powers Export page auto-snapshot.
- Library restore deletes and recreates sessions/sheets/blocks/pipeline/market but does not restore module pathway or module responses.
- Library export includes discovery sessions but not all newer project fields such as `pathway_id`, `ai_partner_style`, categories, pathway lock status, module pathways, module responses, prompt kits, sprint plans, shares, comments, ratings, or integrations.

## Broken Or Incomplete Backend/Frontend Contracts

### Sharing routes are mismatched

Backend routes:

- `POST /api/v1/sharing/{project_id}`
- `GET /api/v1/sharing/{project_id}/status`
- `DELETE /api/v1/sharing/{project_id}`

Frontend `ShareDialog` calls:

- `GET /sharing/projects/${projectId}/share`
- `POST /sharing/projects/${projectId}/share`
- `DELETE /sharing/projects/${projectId}/share`

Result: project sharing from the Library UI is currently broken.

### Inbox promotion uses a non-existent Project field

`backend/app/routers/inbox.py:120` creates `Project(owner_id=current_user.id)`, but the `Project` model has `user_id`, not `owner_id`.

Result: promoting an inbox item to a project should raise an invalid keyword argument error.

### Branch creation uses a non-existent Project field

`backend/app/routers/branching.py:56` also uses `owner_id=current_user.id`.

Result: branch creation should fail.

Additional branching gaps:

- Router prefix is `/branching`, but AGENTS.md documents `/projects/{id}/branch`.
- Only create/list exists. Compare and merge are documented but not implemented.
- Branching does not deep-copy design sheet, sessions, blocks, pipeline, or other child records.

### External integrations are only credential CRUD

AGENTS.md describes provider OAuth, callbacks, disconnect, and push:

- `/integrations/{provider}/auth`
- `/integrations/{provider}/callback`
- `/integrations/{provider}/push/{project_id}`

Actual code only has:

- list integrations,
- create integration with raw token,
- update token/config,
- delete integration,
- list providers.

Tokens are stored as plaintext in `external_integrations.access_token` and `refresh_token`, despite AGENTS.md saying encrypted token storage.

### Sharing feedback/ratings are backend-only

Backend has comments and ratings endpoints, plus `allow_feedback` and `allow_ratings` model fields.

Frontend has no `CommentSection`, `StarRating`, or `FeedbackPanel` implementation in the current file tree. `ShareDialog` has no feedback/rating toggles and `CreateShareRequest` has no corresponding payload fields.

### Prompt Kit route is not exposed in navigation

Backend prompt kit routes exist under `/projects/{project_id}/prompts`, and prompt package export exists under `/projects/{project_id}/export/prompt-package`. There is no dedicated current Prompt Kit page in the actual frontend routes, despite the product docs describing one.

## Security And Authorization Findings

These are targeted audit findings, not a full formal repository-wide security scan.

### P0/P1 security issues

1. Sprint read/update/delete endpoints do not verify project ownership.
   - `backend/app/routers/sprints.py:44` gets a sprint plan by project id without checking that the project belongs to `current_user`.
   - `backend/app/routers/sprints.py:66` updates by project id without ownership verification.
   - `backend/app/routers/sprints.py:115` deletes by project id without ownership verification.

2. Sharing status and revoke endpoints do not verify project ownership.
   - `backend/app/routers/sharing.py:70` gets share status by project id without confirming ownership.
   - `backend/app/routers/sharing.py:94` revokes share by project id without confirming ownership.

3. Public shared CSV/comments/ratings do not consistently enforce expiry/password semantics.
   - `/sharing/public/{token}` checks expiry and password.
   - `/sharing/public/{token}/csv`, comments, and ratings do not check expiry.
   - Comments and ratings do not require any proof that the viewer passed a password-protected share gate.

4. Resend inbound email webhook has no signature verification.
   - `backend/app/routers/webhooks.py` trusts any POST body and only checks whether `to` matches a user's inbox email.

5. External integration tokens are stored plaintext.
   - `backend/app/models/external_integration.py` stores `access_token` and `refresh_token` as text.
   - `backend/app/routers/integrations.py` writes raw tokens directly.

6. Clerk token verification does not validate issuer/audience/authorized party.
   - `backend/app/core/clerk.py` verifies signature/timing but does not constrain issuer or audience.
   - At minimum, production settings should include the expected issuer and authorized party/audience checks for the deployed Clerk instance.

### Dependency audit

`npm audit` reports:

- critical: `@clerk/shared`
- high: `@clerk/clerk-react`, `axios`, `flatted`, `picomatch`, `vite`
- moderate: `brace-expansion`, `follow-redirects`, `postcss`

`npm ci` also warns that `@clerk/clerk-react@5.61.3` is deprecated and says to use `@clerk/react`.

## Feature Status By Area

| Area | Current status | Notes |
| --- | --- | --- |
| Auth | Partially production-ready | Clerk frontend/backend wiring exists; token validation should be hardened. |
| Billing | Basic wiring exists | Checkout and portal exist; entitlement enforcement is not visible across feature gates. |
| Project creation | Functional | Category + idea + partner creates a project. |
| Discovery | Implemented but not resume-safe | SSE chat and extraction exist; start flow creates duplicate sessions. |
| Design sheet | Implemented | Persists, but frontend does not load it when resuming discovery. |
| Library | Useful but thin | Project list/snapshots/import/export exist; lacks workflow progress/resume intelligence. |
| Blocks | Basic implementation | AI generation and CRUD exist; no drag/drop despite docs claiming dnd-kit. |
| Pipeline | Basic implementation | AI recommendation and swaps exist; compatibility checks are minimal. |
| Prompt Kit | Backend/service exists | Dedicated frontend page is missing; export prompt package exists. |
| Market analysis | Substantial | Large frontend page and backend SSE/export routes exist. |
| Sprint planner | Substantial but ownership bug | UI and export exist; backend get/update/delete need authorization checks. |
| Sharing | Backend partial, frontend broken | Route mismatch, no feedback UI, security gaps. |
| Idea inbox | Mostly implemented | Manual/email capture exists; promote currently broken due `owner_id`. |
| Templates | Implemented | 160-template migration exists, frontend grid uses `/templates`. |
| Branching | Mostly incomplete | Create/list only, create broken, no deep copy/compare/merge. |
| Integrations | Placeholder/CRUD only | No OAuth, no push, no token encryption. |
| Module pathway | Partially implemented | Assembly/lock/module sessions exist; module session resume behavior is weak. |
| Tests | Very thin | Only partner style tests are present. |

