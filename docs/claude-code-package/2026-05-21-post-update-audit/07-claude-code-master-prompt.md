# Claude Code Master Prompt

Use this prompt in a new Claude Code session.

```text
You are working in the Ide/AI repository.

First read:

1. AGENTS.md
2. CLAUDE.md
3. CONTEXT_HANDOFF.md
4. docs/claude-code-package/2026-05-21-post-update-audit/README.md
5. docs/claude-code-package/2026-05-21-post-update-audit/01-product-intent.md
6. docs/claude-code-package/2026-05-21-post-update-audit/02-current-state-post-update.md
7. docs/claude-code-package/2026-05-21-post-update-audit/03-priority-findings.md

The first implementation target is:

docs/claude-code-package/2026-05-21-post-update-audit/04-plan-discovery-library-resume.md

Implement that plan task by task. Do not start a dev server or browser preview. The project owner handles manual preview.

Critical first fix:

Discovery autosave currently risks overwriting backend messages with stale client state because frontend/src/pages/Discovery.tsx registers an unmount cleanup that depends on saveProgress, and saveProgress depends on messages/stage. The backend progress endpoint then blindly replaces session.messages. Fix this before doing lower-priority work.

After the discovery/library/pathway resume work is complete and verified, continue in this order:

1. docs/claude-code-package/2026-05-21-post-update-audit/05-plan-security-webhooks-sharing-entitlements.md
2. docs/claude-code-package/2026-05-21-post-update-audit/06-plan-frontend-quality-and-product-completion.md

Before changing code, run:

git status --short

Do not revert user changes.

Use Windows-safe commands in PowerShell:

cd frontend
npm.cmd run lint
npm.cmd run build
npm.cmd audit --json

Backend syntax check:

cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python -m compileall app -q

Backend tests require dependencies and likely TEST_DATABASE_URL. Do not claim tests pass unless they were actually run.

When fixing Resend webhook verification, use the official Resend/Svix verification model, not a bare HMAC digest:

https://resend.com/docs/dashboard/webhooks/verify-webhooks-requests
```

