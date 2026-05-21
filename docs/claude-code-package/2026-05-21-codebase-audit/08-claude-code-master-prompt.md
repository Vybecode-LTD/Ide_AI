# Claude Code Master Prompt

Use this prompt in a new Claude Code session.

```text
You are working in the Ide/AI repository.

First read:

1. AGENTS.md
2. docs/claude-code-package/2026-05-21-codebase-audit/README.md
3. docs/claude-code-package/2026-05-21-codebase-audit/01-product-intent.md
4. docs/claude-code-package/2026-05-21-codebase-audit/02-current-state-audit.md
5. docs/claude-code-package/2026-05-21-codebase-audit/03-priority-roadmap.md

The first implementation target is:

docs/claude-code-package/2026-05-21-codebase-audit/04-plan-discovery-resume-autosave.md

Follow that plan task by task. Do not start a dev server or browser preview. The project owner handles manual preview. Use Windows-safe commands such as npm.cmd when running frontend commands from PowerShell.

After the discovery resume fix is implemented and verified, continue in order:

1. docs/claude-code-package/2026-05-21-codebase-audit/05-plan-library-sharing-branching.md
2. docs/claude-code-package/2026-05-21-codebase-audit/06-plan-security-hardening.md
3. docs/claude-code-package/2026-05-21-codebase-audit/07-plan-product-completion.md

Important known issue:

Discovery progress is currently not resumed because frontend/src/pages/Discovery.tsx posts to /discovery/start on every mount, backend/app/routers/discovery.py calls discovery_service.create_session, and backend/app/services/discovery_service.py always creates a fresh DiscoverySession. Fix this first.

Before changing code, run:

git status --short

Do not revert user changes. Make focused commits after each working vertical slice if the user asks for commits.

Verification commands to prefer:

cd frontend
npm.cmd run build
npm.cmd audit

Backend pytest may require installing backend dependencies and pytest. If dependencies are unavailable, at least run:

cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python -m compileall app -q

Do not claim tests passed unless they were actually run.
```

