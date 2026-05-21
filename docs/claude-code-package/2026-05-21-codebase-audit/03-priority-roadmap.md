# C. Priority Roadmap To Reach The Product Goals

## Guiding Principle

Fix durable workflow state before adding new feature surface. Ide/AI's product promise depends on users trusting that the system remembers their progress.

## P0 - Must Fix First

### 1. Make discovery resumable

Why: This is the user-reported bug and it breaks the primary product workflow.

Required outcome:

- Re-entering `/discovery/:projectId` resumes the latest active discovery session.
- Existing chat messages, stage, partner style, and design sheet load immediately.
- A new discovery session is created only when no resumable session exists or when the caller explicitly requests a new session.

Plan: `04-plan-discovery-resume-autosave.md`

### 2. Fix runtime-breaking field mismatches

Required outcome:

- Inbox promotion uses `user_id`, not `owner_id`.
- Branch creation uses `user_id`, not `owner_id`.
- Add tests or at least import-level checks to prevent invalid model constructor keywords.

Plan: `05-plan-library-sharing-branching.md`

### 3. Fix sharing route mismatch

Required outcome:

- `ShareDialog` calls the routes that the backend actually exposes, or backend compatibility routes are added.
- Sharing create/status/revoke all work from Library.
- Ownership checks are added to status/revoke.

Plan: `05-plan-library-sharing-branching.md`

### 4. Patch authorization gaps

Required outcome:

- Sprint get/update/delete verify project ownership.
- Sharing status/revoke verify project ownership.
- Public sharing secondary endpoints respect expiry and password rules.

Plan: `06-plan-security-hardening.md`

## P1 - Stabilize The Workflow

### 5. Add project progress metadata to Library

Required outcome:

- Library rows show discovery stage, message count, design sheet confidence, block count, pathway status, and last activity.
- Open/Resume button routes to the most relevant next screen.

Plan: `05-plan-library-sharing-branching.md`

### 6. Unify snapshots and versions

Required outcome:

- Decide whether `project_snapshots` or `versions` owns snapshot history.
- Export page "Save Snapshot" and Library "Create Snapshot" should use the same model/service.
- Restore should cover current project artifacts, including module pathway/module responses.

Plan: `05-plan-library-sharing-branching.md`

### 7. Make module sessions resumable

Required outcome:

- `POST /modules/{project_id}/{module_id}/start` returns existing active messages instead of overwriting them.
- Completed modules return summary and existing transcript so UI can show completion context.

Plan: `07-plan-product-completion.md`

### 8. Add tests around persistence and ownership

Required outcome:

- Discovery resume tests.
- Inbox promote test.
- Sharing route/ownership tests.
- Sprint ownership tests.
- Basic frontend endpoint contract tests or typed API helper coverage.

Plan: all implementation plans include test tasks.

## P2 - Complete Advertised Product Surface

### 9. Complete sharing feedback and ratings UI

Required outcome:

- ShareDialog includes "Allow comments" and "Allow ratings" toggles.
- SharedProject renders comments and ratings when enabled.
- Owner can view feedback summary.

### 10. Implement real external integrations or mark as unavailable until scoped

Required outcome:

- OAuth auth/callback/push endpoints exist for providers that are advertised as active, or
- UI clearly marks integrations as placeholders.
- Stored credentials are encrypted.

### 11. Complete branching

Required outcome:

- Branch creation deep-copies child records.
- Branch list appears in Library.
- Compare and merge endpoints are implemented or removed from docs.

### 12. Dedicated Prompt Kit page

Required outcome:

- Prompt kit generation, rewrite, copy sections, and zero-dev language mode are available from the project workflow.
- Existing `/projects/{project_id}/prompts` backend routes are actually used.

### 13. Reconcile docs and branding

Required outcome:

- Remove stale `ideaFORGE` prompt personas or intentionally keep them only where product copy wants legacy naming.
- Update AGENTS.md, CONTEXT_HANDOFF.md, ARCHITECTURE.md, README.md, and env docs to match current code.
- Document React 19, Vite 7, Clerk package upgrade path, and current route map.

## Suggested Execution Order

1. Discovery resume/autosave.
2. Runtime field mismatch fixes.
3. Sharing route and authorization fixes.
4. Sprint authorization fixes.
5. Library progress metadata and resume routing.
6. Snapshot/version unification.
7. Module session resume.
8. Dependency/security hardening.
9. Sharing feedback UI.
10. Branching deep-copy/compare/merge.
11. Integrations.
12. Prompt Kit page.
13. Docs cleanup.
