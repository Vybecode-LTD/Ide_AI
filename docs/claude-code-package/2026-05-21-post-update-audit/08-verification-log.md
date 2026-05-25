# Verification Log

Date: 2026-05-21

## Repository State

Command:

```powershell
git status --short
```

Result before this new audit package was added:

```text
?? AGENTS.md
```

Recent commits:

```text
d411919 fix: library.py __uuid typo from replace-all - correct to _uuid
a846459 fix: library.py NameError - uuid.UUID references after _uuid rename
e06aab2 fix: resolve placeholder emails and stale inbox domains
bbde045 fix: update FROM_EMAIL to use send.myide.ai sending domain
8dfa51b fix: increase healthcheck timeout, update email domain to myide.ai
75cb690 feat: comprehensive codebase audit - P0 fixes, security hardening, product completion
0570936 fix: redesign chip system - AI embeds answer options, smart fallback parsing
e49e3ba fix: stage-specific chip fallbacks, sidebar shows only Discovery pre-pathway
1b15b37 fix: only show dynamic modules in sidebar after pathway is locked
d9a6a61 fix: critical audit fixes - SSE auth, migration path, model imports
```

## CodeRabbit

Command:

```powershell
coderabbit --version
```

Result:

```text
coderabbit : The term 'coderabbit' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

Installer command required by the CodeRabbit skill:

```powershell
curl.exe -fsSL https://cli.coderabbit.ai/install.sh | sh
```

Result:

```text
sh : The term 'sh' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

Conclusion:

CodeRabbit review was not run. Findings in this audit are manual code inspection findings and targeted security/frontend audit findings.

## Frontend Build

Command:

```powershell
cd frontend
npm.cmd run build
```

Result:

```text
frontend@0.0.0 build
tsc -b && vite build
vite v7.3.3 building client environment for production...
676 modules transformed.
built in 2.73s
```

Status: passed.

Note:

Node emitted:

```text
[DEP0205] DeprecationWarning: module.register() is deprecated. Use module.registerHooks() instead.
```

## Frontend npm Audit

Command:

```powershell
cd frontend
npm.cmd audit --json
```

Result:

```json
{
  "vulnerabilities": {},
  "metadata": {
    "vulnerabilities": {
      "info": 0,
      "low": 0,
      "moderate": 0,
      "high": 0,
      "critical": 0,
      "total": 0
    }
  }
}
```

Status: passed.

## Frontend Lint

Command:

```powershell
cd frontend
npm.cmd run lint
```

Result:

```text
19 problems (12 errors, 7 warnings)
```

Notable errors:

- `TemplateGrid.tsx:55` and `TemplateGrid.tsx:66`: synchronous setState in effect.
- `Sidebar.tsx:105` and `Sidebar.tsx:115`: synchronous setState in effect.
- `PartnerSelector.tsx:28`: synchronous setState in effect.
- `FeedbackPanel.tsx:42`: synchronous setState in effect.
- `StageInterlude.tsx:64`: `dismiss` accessed before declaration.
- `CategorySelect.tsx:16`: Fast Refresh export rule.
- `Home.tsx:37` and `Home.tsx:57`: synchronous setState in effect.
- `MarketAnalysis.tsx:221`: render-time reassignment of `cumulative`.
- `PathwayReview.tsx:80`: synchronous setState in effect.

Status: failed.

## Backend Syntax Compile

Command:

```powershell
cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python -m compileall app -q
```

Result: no output.

Status: passed.

## Backend Pytest

Command:

```powershell
cd backend
python -m pytest tests -q
```

Result:

```text
C:\Python314\python.exe: No module named pytest
```

Status: blocked.

Additional note:

`backend/tests/test_discovery_resume.py` requires `db_session` and `test_user` fixtures, but no `backend/tests/conftest.py` exists.

## Backend App Import

Command:

```powershell
cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python - << equivalent:
from app.main import app
print(app.title)
print(len(app.routes))
```

Result:

```text
ModuleNotFoundError: No module named 'fastapi'
```

Status: blocked by missing backend runtime dependencies in local Python.

## External Source Checked

Resend webhook verification docs:

```text
https://resend.com/docs/dashboard/webhooks/verify-webhooks-requests
```

Reason:

The current inbound email webhook uses bare HMAC verification. Resend documents SDK/Svix verification with raw payload and the Svix headers.

