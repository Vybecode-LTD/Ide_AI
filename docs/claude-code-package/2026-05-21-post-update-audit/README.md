# Ide/AI Post-Update Audit Package

Date: 2026-05-21

This package is a fresh audit after the Claude Code update represented by commit `75cb690` and follow-up fixes through `d411919`.

It follows the same parameters as the previous audit:

1. Describe what the application is attempting to achieve overall.
2. Describe where the current codebase stands against that goal.
3. Provide a prioritized set of implementation plans that can be handed to Claude Code.

## Reading Order

1. `01-product-intent.md`
2. `02-current-state-post-update.md`
3. `03-priority-findings.md`
4. `04-plan-discovery-library-resume.md`
5. `05-plan-security-webhooks-sharing-entitlements.md`
6. `06-plan-frontend-quality-and-product-completion.md`
7. `07-claude-code-master-prompt.md`
8. `08-verification-log.md`

## Executive Summary

The Claude Code update substantially improved the codebase. The frontend production build now passes, npm audit reports zero vulnerabilities, discovery start/resume is no longer a fresh-session-only endpoint, the old `owner_id` crashes were fixed, sharing routes were aligned, module sessions can resume, prompt kit UI was added, and several security checks were attempted.

The app is now closer to the intended Ide/AI workflow, but it is not production-ready yet. The most important remaining issue is that the discovery autosave implementation can overwrite canonical server-side messages with stale client state. This means the original "discovery progress loss" class of bug is improved but not fully closed.

The other major remaining gaps are:

- Existing users affected by the old discovery bug may still be resumed into the wrong empty session.
- Library smart resume can still route users back to Discovery forever because discovery sessions are never marked complete.
- Module pathway completion is frontend-only and race-prone; the backend never marks the pathway complete.
- Resend webhook verification is implemented as bare HMAC but Resend documents Svix verification with `svix-id`, `svix-timestamp`, and `svix-signature`.
- Password-protected share links still expose comments and ratings endpoints by token alone.
- Entitlement gates are inconsistent and not count-based for count-limited features.
- `npm.cmd run lint` currently fails with 12 errors and 7 warnings.
- Backend tests still cannot run locally, and the newly added discovery tests require fixtures that do not exist.

## Verification Snapshot

Commands run during this audit:

- `git status --short`: reports only `?? AGENTS.md` before this new package was added.
- `git log --oneline -10`: confirms the post-audit update commits are present.
- `coderabbit --version`: failed because CodeRabbit CLI is not installed.
- `curl.exe -fsSL https://cli.coderabbit.ai/install.sh | sh`: failed because `sh` is not available in this Windows shell.
- `npm.cmd run build`: passed.
- `npm.cmd audit --json`: passed with zero vulnerabilities.
- `npm.cmd run lint`: failed with 12 errors and 7 warnings.
- `python -m compileall app -q`: passed.
- `python -m pytest tests -q`: failed because local Python has no `pytest`.
- Importing `app.main`: failed because local Python lacks backend runtime dependencies such as `fastapi`.

## Plugin Notes

CodeRabbit was requested but could not be run. Do not represent any finding in this package as CodeRabbit output.

Codex Security was used as a targeted security review lens, not as a completed exhaustive repository-wide security scan. The security findings are grounded in inspected code and, for Resend signature verification, checked against the official Resend webhook verification documentation:

- https://resend.com/docs/dashboard/webhooks/verify-webhooks-requests

Build Web Apps guidance was used for frontend quality, React behavior, lint output, and product flow review.

OpenAI Developers was not directly applicable because this repo does not currently call OpenAI APIs; it uses Anthropic for runtime AI. OpenAI and ChatGPT appear only as generated prompt-package targets or template text.

