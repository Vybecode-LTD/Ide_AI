# Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the highest-risk authorization, webhook, credential-storage, and dependency issues found during the targeted codebase audit.

**Architecture:** Prioritize server-side authorization and credential handling. Frontend fixes are helpful, but backend ownership and public endpoint rules are the security boundary.

**Tech Stack:** FastAPI, SQLAlchemy async, Clerk JWTs, Stripe, Resend inbound webhooks, npm/Vite/React dependencies.

---

## Task 1: Fix Sprint Plan Ownership Checks

**Files:**
- Modify: `backend/app/routers/sprints.py`

- [ ] **Step 1: Add owner helper**

```python
async def _verify_project_owner(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
```

- [ ] **Step 2: Use helper in all sprint endpoints**

Add this before fetching/updating/deleting sprint plan in:

- `get_sprint_plan`
- `update_sprint_plan`
- `delete_sprint_plan`

```python
await _verify_project_owner(db, project_id, current_user.id)
```

`generate_sprint_plan` and `export_sprint_csv` already do ownership checks, but can be refactored to use the helper.

- [ ] **Step 3: Regression test**

Create an authenticated request as User B against User A's project id. Expected response is 404 for get/update/delete.

## Task 2: Harden Sharing Public Secondary Endpoints

**Files:**
- Modify: `backend/app/routers/sharing.py`

- [ ] **Step 1: Add share access helper**

```python
def _share_expired(share: ProjectShare) -> bool:
    return bool(share.expires_at and share.expires_at < datetime.now(timezone.utc))


def _raise_if_expired(share: ProjectShare) -> None:
    if _share_expired(share):
        raise HTTPException(status_code=410, detail="Share link has expired")
```

- [ ] **Step 2: Apply expiry check everywhere public**

Call `_raise_if_expired(share)` in:

- `export_shared_csv`
- `get_comments`
- `add_comment`
- `get_ratings`
- `add_rating`

- [ ] **Step 3: Protect CSV for private shares**

If a share is private/password protected, do not let `/csv` bypass verification.

Minimal fix:

```python
if not share.is_public and share.password_hash:
    raise HTTPException(status_code=403, detail="Password verification required")
```

Longer-term fix: issue a short-lived signed viewer access token after `/verify` and require it for CSV/comments/ratings on private shares.

## Task 3: Encrypt External Integration Tokens

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Add: `backend/app/core/encryption.py`
- Modify: `backend/app/routers/integrations.py`
- Modify: `env.example`

- [ ] **Step 1: Add setting**

In `Settings`:

```python
INTEGRATION_TOKEN_KEY: str = ""
```

In `env.example`:

```env
INTEGRATION_TOKEN_KEY=base64-fernet-key
```

- [ ] **Step 2: Add encryption helper**

Create `backend/app/core/encryption.py`:

```python
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    if not settings.INTEGRATION_TOKEN_KEY:
        raise RuntimeError("INTEGRATION_TOKEN_KEY is required for integration credentials")
    return Fernet(settings.INTEGRATION_TOKEN_KEY.encode("utf-8"))


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return value
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return value
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
```

- [ ] **Step 3: Use encryption on write**

In `backend/app/routers/integrations.py`:

```python
from app.core.encryption import encrypt_secret
```

When creating:

```python
access_token=encrypt_secret(payload.access_token),
```

When updating:

```python
if payload.access_token is not None:
    integration.access_token = encrypt_secret(payload.access_token)
```

- [ ] **Step 4: Do not return decrypted tokens**

The current API returns only `has_token`, which is correct. Keep it that way.

- [ ] **Step 5: Migration consideration**

Existing plaintext tokens will remain plaintext unless migrated. Add a one-time migration script or admin task that:

1. Finds integration rows with non-empty tokens.
2. Detects whether they already look like Fernet tokens.
3. Encrypts plaintext values.

Do not log token values.

## Task 4: Verify Resend Inbound Email Webhooks

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/routers/webhooks.py`
- Modify: `env.example`

- [ ] **Step 1: Add a webhook secret setting**

```python
RESEND_WEBHOOK_SECRET: str = ""
```

- [ ] **Step 2: Reject unsigned production requests**

Implement verification according to Resend's current webhook signing docs before deploying. If the project uses Svix-style signatures, follow the Clerk webhook pattern. If Resend uses HMAC headers in the current account configuration, implement HMAC verification against raw request body.

Minimum safe behavior:

```python
if settings.ENVIRONMENT == "production" and not settings.RESEND_WEBHOOK_SECRET:
    raise HTTPException(status_code=500, detail="Inbound email webhook secret is not configured")
```

Then verify the request signature before parsing JSON.

- [ ] **Step 3: Add spam controls**

Add:

- max body size,
- subject/body truncation already exists but keep it,
- rate limiting at Railway/proxy layer if available,
- logging for unknown recipients without storing body.

## Task 5: Harden Clerk JWT Verification

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/core/clerk.py`
- Modify: `env.example`

- [ ] **Step 1: Add expected issuer/audience settings**

```python
CLERK_ISSUER: str = ""
CLERK_AUDIENCE: str = ""
CLERK_AUTHORIZED_PARTIES: list[str] = []
```

- [ ] **Step 2: Verify issuer and audience when configured**

In `jwt.decode`, pass issuer/audience only if configured:

```python
decode_kwargs = {
    "algorithms": ["RS256"],
    "options": {
        "verify_exp": True,
        "verify_iat": True,
        "verify_nbf": True,
    },
}
if settings.CLERK_ISSUER:
    decode_kwargs["issuer"] = settings.CLERK_ISSUER
if settings.CLERK_AUDIENCE:
    decode_kwargs["audience"] = settings.CLERK_AUDIENCE

payload = jwt.decode(token, signing_key.key, **decode_kwargs)
```

- [ ] **Step 3: Verify authorized party when configured**

```python
azp = payload.get("azp")
if settings.CLERK_AUTHORIZED_PARTIES and azp not in settings.CLERK_AUTHORIZED_PARTIES:
    raise jwt.InvalidTokenError("Invalid authorized party")
```

## Task 6: Upgrade Frontend Dependencies

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify imports if Clerk package name changes.

- [ ] **Step 1: Run targeted updates**

Use `npm audit` output to update:

```powershell
npm.cmd install axios@latest vite@latest @clerk/react@latest @clerk/themes@latest
```

If Clerk migration requires replacing package imports, update:

- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/auth/ProtectedRoute.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- sign-in/sign-up pages.

- [ ] **Step 2: Build**

```powershell
npm.cmd run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 3: Audit**

```powershell
npm.cmd audit
```

Expected: no critical/high issues. If moderate dev-only Vite advisories remain, document whether they affect production build output.

## Task 7: Security Acceptance Checklist

- [ ] User B cannot read, update, or delete User A's sprint plan.
- [ ] User B cannot read or revoke User A's share status.
- [ ] Expired shares reject public data, CSV, comments, and ratings.
- [ ] Password-protected shares do not expose CSV/comments/ratings without a verified access mechanism.
- [ ] Integration tokens are encrypted at rest.
- [ ] Inbound email webhook rejects invalid signatures in production.
- [ ] Clerk JWT verification constrains the token to the expected Clerk instance/app.
- [ ] `npm audit` has no critical/high issues.

