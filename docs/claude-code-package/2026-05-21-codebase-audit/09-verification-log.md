# Verification Log

Date: 2026-05-21

## Repository State

Command:

```powershell
git status --short
```

Result:

```text
?? AGENTS.md
```

At the start of the audit, `AGENTS.md` was untracked. This audit package adds new docs under `docs/`.

## Frontend Dependency Install

Command:

```powershell
cd frontend
npm.cmd ci
```

Result:

```text
added 235 packages
9 vulnerabilities (3 moderate, 5 high, 1 critical)
deprecated @clerk/clerk-react@5.61.3
```

## Frontend Build

Command:

```powershell
cd frontend
npm.cmd run build
```

Result: passed.

Important output:

```text
tsc -b && vite build
670 modules transformed
built in 4.80s
```

Node emitted a deprecation warning:

```text
DEP0205: module.register() is deprecated. Use module.registerHooks() instead.
```

## Frontend Audit

Command:

```powershell
cd frontend
npm.cmd audit --json
```

Result: failed due advisories.

Summary:

```text
total: 9
critical: 1
high: 5
moderate: 3
```

Important packages:

- `@clerk/shared`: critical
- `@clerk/clerk-react`: high and deprecated
- `axios`: high
- `vite`: high
- `flatted`: high
- `picomatch`: high
- `brace-expansion`: moderate
- `follow-redirects`: moderate
- `postcss`: moderate

## Backend Tests

Command:

```powershell
cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python -m pytest tests -q
```

Result: could not run.

Reason:

```text
No module named pytest
```

## Backend Syntax Compile

Command:

```powershell
cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python -m compileall app -q
```

Result: passed.

## Backend Import Check

Command:

```powershell
cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
$env:ANTHROPIC_KEY='dummy'
$env:CLERK_JWKS_URL='https://example.com/.well-known/jwks.json'
python -c "from app.main import app; print(app.title); print(len(app.routes))"
```

Result: could not run.

Reason:

```text
ModuleNotFoundError: No module named 'fastapi'
```

## CodeRabbit

Command:

```powershell
coderabbit --version
```

Result:

```text
coderabbit is not recognized
```

Install attempt:

```powershell
curl.exe -fsSL https://cli.coderabbit.ai/install.sh | sh
```

Result:

```text
sh is not recognized
```

Conclusion: CodeRabbit CLI review was not performed. Findings in this package are manual codebase audit findings and should not be represented as CodeRabbit output.

