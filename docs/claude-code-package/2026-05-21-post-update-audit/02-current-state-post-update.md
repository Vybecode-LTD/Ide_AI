# B. Current State After Claude Code Update

## Summary

The update moved the codebase materially forward. Several prior blockers are fixed or partially fixed:

- `POST /discovery/start` now calls `create_or_resume_session`.
- `SessionCreate` has `force_new`.
- Discovery page hydrates messages and sheet state.
- `owner_id` crashes in inbox promotion and branch creation were fixed.
- ShareDialog route calls now match the backend.
- Sharing ownership checks were added for share status and revoke.
- Sprint get/update/delete ownership checks were added.
- Sharing feedback components now exist.
- PromptKit page and route are wired.
- npm audit is clean.

The update also introduced or exposed several important remaining defects:

- Discovery auto-save can write stale messages back to the server.
- Existing users with old empty sessions may still resume the wrong session.
- Library smart resume often cannot progress beyond Discovery because discovery sessions are never marked complete.
- Pathway completion is not persisted by the backend.
- Resend webhook signature verification does not match Resend's documented Svix verification model.
- Password-protected shares do not protect comment and rating endpoints.
- Entitlements are incomplete and bypassable.
- Frontend lint now fails with React hook/compiler rules.
- Backend tests are not runnable in this checkout.

## Verification Results

### Passed

- `npm.cmd run build` in `frontend/` passed.
- `npm.cmd audit --json` in `frontend/` reported zero vulnerabilities.
- `python -m compileall app -q` in `backend/` passed.

### Failed Or Blocked

- `npm.cmd run lint` failed with 12 errors and 7 warnings.
- `python -m pytest tests -q` failed because the local Python environment has no `pytest`.
- Importing `app.main` failed because the local Python environment lacks backend runtime dependencies such as `fastapi`.
- CodeRabbit CLI was not installed. The documented installer failed because `sh` is not present in this Windows shell.

## Current Product Status By Area

| Area | Status | Notes |
|---|---|---|
| Clerk auth | Mostly implemented | JWT verification is hardened when optional env vars are configured, but docs/env parsing need cleanup. |
| Billing | Partially implemented | Checkout/portal/webhook exist. Entitlement enforcement is inconsistent. |
| Project creation | Partially implemented | Blank creation checks project limits. Templates, imports, inbox promotion, and branches bypass project limits. |
| Discovery resume | Improved but unsafe | Start/resume is idempotent, but auto-save can overwrite server messages with stale client state. |
| Library progress | Partially implemented | Metadata fields exist, but resume path depends on status values that are never set. |
| Modular pathway | Partially implemented | Module resume exists, but pathway completion is not persisted. |
| Blocks/pipeline | Largely implemented | Ownership checks appear present. Not deeply revalidated in this pass. |
| PromptKit | Implemented MVP | Page and backend routes exist. 403 handling and usage counting are incomplete. |
| Market analysis | Implemented MVP | Generation is paid-gated, but usage counts are not enforced. |
| Sprint planner | Implemented MVP | Ownership fixed. Entitlement limit exists in config but is not enforced. |
| Sharing | Improved but security incomplete | Password-protected share content is gated, but feedback endpoints are not. |
| Branching | Partially implemented | Deep copy exists but omits some artifacts and fields. Merge can drop market analysis. |
| Integrations | De-scoped | Unconnected providers return `coming_soon`, but manual token endpoints still exist and require encryption env. |
| Tests | Weak | New discovery tests require missing fixtures. No frontend test harness. |
| Docs | Mixed | README improved. AGENTS.md and env docs are stale in several important places. |

## Discovery Resume State

Relevant files:

- `backend/app/schemas/session.py`
- `backend/app/services/discovery_service.py`
- `backend/app/routers/discovery.py`
- `frontend/src/pages/Discovery.tsx`
- `backend/tests/test_discovery_resume.py`

What improved:

- `SessionCreate` now has `force_new: bool = False`.
- `create_or_resume_session` returns an existing active session by default.
- `start_session` uses `create_or_resume_session`.
- `Discovery.tsx` loads `/discovery/{session_id}/sheet`.
- `Discovery.tsx` skips `/init` when the returned session already has messages.

Current issue 1: stale client auto-save.

- `frontend/src/pages/Discovery.tsx:89-95` defines `saveProgress` with `messages` and `stage` captured from React state.
- `frontend/src/pages/Discovery.tsx:125-130` registers an unmount cleanup with `saveProgress` in its dependency list.
- Because `saveProgress` changes whenever `messages` or `stage` changes, this cleanup runs on ordinary state changes, not only on page unmount.
- That cleanup can send the previous render's messages to `PATCH /discovery/{session_id}/progress`.
- `backend/app/routers/discovery.py:239-241` blindly replaces `session.messages` and `session.stage` with the supplied client payload.

Impact:

- The backend already saves the user's message before streaming at `backend/app/routers/discovery.py:142-144`.
- A cleanup from the previous render can later overwrite that persisted user message with an older message array.
- This can recreate the same class of "progress loss" that the update attempted to fix.

Current issue 2: old empty sessions are not recovered.

- `backend/app/services/discovery_service.py:36-50` picks the latest active session by `updated_at` and `created_at`.
- Before the fix, the app created fresh empty sessions on re-entry.
- If an affected project has a newer empty active session and an older non-empty active session, the new resume helper will still return the empty one.

Impact:

- Users who already experienced the bug may still appear to have lost progress even after the code update.

Current issue 3: backend tests are non-executable.

- `backend/tests/test_discovery_resume.py` references `db_session` and `test_user` fixtures.
- No `backend/tests/conftest.py` exists.
- The file itself says the tests will fail until fixtures are added.

Impact:

- The most important bug fix is not covered by runnable tests.

## Library State

Relevant files:

- `backend/app/routers/library.py`
- `backend/app/services/library_service.py`
- `frontend/src/pages/Library.tsx`

What improved:

- Library list includes `discovery_stage`, `discovery_message_count`, `design_confidence`, `block_count`, `pathway_status`, `pathway_locked`, and `recommended_resume_path`.
- Frontend renders progress labels and confidence.

Current issue: resume path does not match real lifecycle.

- `backend/app/routers/library.py:36-38` sends any project with an active session to `/discovery/{project_id}`.
- Discovery sessions are created with `status="active"` and are not marked complete when stage reaches `confirm`.
- `frontend/src/pages/Library.tsx:225-233` labels a project with `discovery_stage === "confirm"` as ready for pathway review, but the backend resume path may still be `/discovery/{id}`.

Impact:

- The UI can say "Pathway review" while the button routes the user back to Discovery.
- Library still cannot reliably act as the project management cockpit.

## Modular Pathway State

Relevant files:

- `backend/app/routers/modules.py`
- `backend/app/routers/module_pathway.py`
- `frontend/src/stores/modulePathwayStore.ts`
- `frontend/src/pages/PathwayExecute.tsx`
- `frontend/src/pages/ModuleSession.tsx`

What improved:

- Starting an active module returns existing messages.
- Starting a complete module returns existing transcript and extracted output.

Current issue 1: pathway completion is not persisted.

- `backend/app/routers/modules.py:274-283` marks an individual module response complete.
- No code updates `ModulePathway.status` to `complete` when all modules are complete or skipped.
- `backend/app/routers/modules.py:318-329` marks skipped modules but also does not update pathway completion.

Current issue 2: frontend completion calculation is race-prone.

- `frontend/src/pages/PathwayExecute.tsx:38-47` calls `fetchPathway`, `fetchResponses`, and possibly `assemble` without awaiting sequence.
- `frontend/src/stores/modulePathwayStore.ts:124-131` calls `checkCompletion` after fetching responses.
- `checkCompletion` returns early if `pathway` has not arrived yet.
- `fetchPathway` does not call `checkCompletion` after setting `pathway`.

Impact:

- A complete pathway can still render as incomplete.
- Library metadata can stay stuck at `pathway_status === "active"`.

## Sharing State

Relevant files:

- `backend/app/routers/sharing.py`
- `backend/app/services/sharing_service.py`
- `frontend/src/components/sharing/ShareDialog.tsx`
- `frontend/src/components/sharing/CommentSection.tsx`
- `frontend/src/components/sharing/StarRating.tsx`
- `frontend/src/components/sharing/FeedbackPanel.tsx`
- `frontend/src/pages/SharedProject.tsx`

What improved:

- Frontend share routes now call `/sharing/{projectId}/status`, `POST /sharing/{projectId}`, and `DELETE /sharing/{projectId}`.
- Backend status and revoke endpoints verify ownership.
- Comments, ratings, and feedback components exist.
- Expiry checks were added to public share data, CSV, comments, and ratings.

Current issue: password-protected feedback bypass.

- `backend/app/routers/sharing.py:157-159` gates the main shared project response when password is required.
- `backend/app/routers/sharing.py:246-335` exposes comments and ratings with only the share token.
- There is no viewer verification token, signed cookie, or password check for comment/rating reads or writes.

Impact:

- Anyone with the private share token can read comments, post comments, read rating summaries, and post ratings without the password.
- This undermines the privacy model for password-protected shares.

## Webhook Security State

Relevant files:

- `backend/app/routers/webhooks.py`
- `backend/app/routers/clerk_webhook.py`
- `backend/app/core/config.py`

What improved:

- Inbound email webhook has a production guard requiring `RESEND_WEBHOOK_SECRET`.
- Inbound email webhook has a 256 KB body limit.
- Clerk webhook uses Svix verification.

Current issue: Resend verification is not implemented using Resend/Svix semantics.

- `backend/app/routers/webhooks.py:23-34` computes `HMAC(secret, raw_body, sha256).hexdigest()`.
- It compares that to `resend-signature` or `svix-signature`.
- Resend's official docs show `svix-id`, `svix-timestamp`, and `svix-signature`, verified with Resend SDK or Svix's `Webhook.verify`.
- The documented `svix-signature` value is versioned/base64 formatted, not a bare hex digest.

Source:

- https://resend.com/docs/dashboard/webhooks/verify-webhooks-requests

Impact:

- A correctly signed Resend webhook may be rejected in production.
- Replay protection from Svix timestamp/id verification is not active.
- Duplicate webhook delivery is not idempotently handled.

## Entitlement State

Relevant files:

- `backend/app/services/entitlement_service.py`
- `backend/app/routers/projects.py`
- `backend/app/routers/templates.py`
- `backend/app/routers/inbox.py`
- `backend/app/routers/branching.py`
- `backend/app/routers/library.py`
- `backend/app/routers/prompts.py`
- `backend/app/routers/market.py`
- `backend/app/routers/sprints.py`

What improved:

- `check_project_limit` gates `POST /projects`.
- `check_feature` gates prompt kit generation and market generation for free users.
- `/auth/me/entitlements` exists.

Current issue 1: project limit bypass.

The following paths create projects without checking `check_project_limit`:

- `POST /templates/{template_id}/use`
- `POST /inbox/{item_id}/promote`
- `POST /branching/{project_id}/branch`
- `POST /library/import`

Current issue 2: count limits are not counted.

- `PLAN_LIMITS` defines `prompt_packages`, `market_analysis`, and `sprint_plans` as count-limited features.
- `check_feature` only checks whether a limit is greater than zero.
- A Basic user with `prompt_packages: 10` can generate more than 10 prompt kits unless another system prevents it.

Current issue 3: sprint plan limit is unused.

- `sprint_plans` exists in `PLAN_LIMITS`.
- `backend/app/routers/sprints.py` does not call entitlement checks.

Current issue 4: frontend 403 handling is weak.

- Home catches project creation errors silently.
- PromptKit logs generation failures without showing an upgrade prompt.
- Market/Sprint streaming code throws generic HTTP errors.

Impact:

- Users can bypass paid limits.
- Legitimate users hit confusing failures instead of upgrade flows.

## Branching And Snapshot State

Relevant files:

- `backend/app/routers/branching.py`
- `backend/app/services/library_service.py`

What improved:

- Branch creation no longer uses invalid `owner_id`.
- Branch creation now deep-copies many child records.
- Compare and merge endpoints exist.

Current issues:

- `_copy_child_records` does not copy `DesignSheet.fields_data`.
- `_copy_child_records` does not copy `DiscoverySession.ai_partner_style`.
- `_copy_child_records` does not copy `ModuleResponse.completed_at`.
- `_copy_child_records` does not copy `MarketAnalysis`.
- `merge_branch` deletes parent `MarketAnalysis` but `_copy_child_records` does not restore branch `MarketAnalysis`.
- There is no obvious frontend compare/merge surface in the current file tree.

Impact:

- Branches and merges can silently drop pathway-specific sheet fields, partner style, module timestamps, and market analysis.

## Frontend Quality State

Relevant files:

- `frontend/src/components/tutorial/StageInterlude.tsx`
- `frontend/src/components/home/TemplateGrid.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/partner/PartnerSelector.tsx`
- `frontend/src/components/sharing/FeedbackPanel.tsx`
- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/MarketAnalysis.tsx`
- `frontend/src/pages/PathwayReview.tsx`

Build passes, but lint fails. Notable lint findings:

- `StageInterlude.tsx:64` calls `dismiss()` before `dismiss` is declared.
- Multiple components call `setState` synchronously inside effects.
- `MarketAnalysis.tsx:221` mutates `cumulative` during render.
- Several hooks have missing dependencies.
- `CategorySelect.tsx` violates Fast Refresh export rules.

Impact:

- This is not just style. The `StageInterlude` issue is a real hook closure/order problem, and the discovery autosave issue is exactly the kind of stale closure bug lint discipline should prevent.

## Docs And Configuration State

What improved:

- Root `README.md` is no longer the generic Vite template.
- `CLAUDE.md` and `CONTEXT_HANDOFF.md` were updated for the new work.

Remaining mismatches:

- `AGENTS.md` still says React 18, Codex model naming, old stores, and migration chain 001-023.
- `CONTEXT_HANDOFF.md` says migration chain 001-023, but `024_expand_templates_160.py` exists.
- `README.md` and `CONTEXT_HANDOFF.md` mention `ANTHROPIC_API_KEY`, while code uses `ANTHROPIC_KEY`.
- `env.example` still uses `noreply@ideaforge.dev` and `inbox.ideaforge.dev`, while code defaults to `send.myide.ai` and `inbox.myide.ai`.
- `env.example` does not list `RESEND_WEBHOOK_SECRET`, `INTEGRATION_TOKEN_KEY`, `CLERK_ISSUER`, `CLERK_AUDIENCE`, or `CLERK_AUTHORIZED_PARTIES`.
- `frontend/README.md` is still the default React/Vite template.

Impact:

- Deployment and future agent work can drift again if the wrong source of truth is read.

