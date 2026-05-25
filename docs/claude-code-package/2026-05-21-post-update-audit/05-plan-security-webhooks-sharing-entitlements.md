# Security, Webhooks, Sharing, And Entitlements Implementation Plan

> For Claude Code: implement this plan after the discovery/library resume fixes. Keep backend authorization and privacy controls as the source of truth.

## Goal

Close the remaining security and commercial-control gaps introduced or left open after the update.

## Task 1: Replace Resend HMAC With Svix Verification

### Files

- Modify `backend/app/routers/webhooks.py`
- Modify `backend/app/models/idea_inbox.py` if idempotency storage needs a column
- Add Alembic migration if idempotency storage is persisted
- Update `env.example`

### Background

Current code:

```python
expected = hmac.new(
    settings.RESEND_WEBHOOK_SECRET.encode("utf-8"),
    raw_body,
    hashlib.sha256,
).hexdigest()
return hmac.compare_digest(expected, signature)
```

This does not match Resend's documented verification. Resend documents Svix-style headers:

- `svix-id`
- `svix-timestamp`
- `svix-signature`

Official docs:

- https://resend.com/docs/dashboard/webhooks/verify-webhooks-requests

### Step 1: Use `svix.Webhook`

The backend already depends on `svix`. Replace `_verify_resend_signature` with:

```python
from svix.webhooks import Webhook, WebhookVerificationError

def _verify_resend_webhook(raw_body: bytes, headers: dict[str, str]) -> dict:
    if not settings.RESEND_WEBHOOK_SECRET:
        raise RuntimeError("RESEND_WEBHOOK_SECRET is required")

    wh = Webhook(settings.RESEND_WEBHOOK_SECRET)
    return wh.verify(
        raw_body.decode("utf-8"),
        {
            "svix-id": headers.get("svix-id", ""),
            "svix-timestamp": headers.get("svix-timestamp", ""),
            "svix-signature": headers.get("svix-signature", ""),
        },
    )
```

Then in the route:

```python
try:
    payload = _verify_resend_webhook(raw_body, request.headers)
except WebhookVerificationError:
    raise HTTPException(status_code=401, detail="Invalid webhook signature")
```

If local development must allow unsigned requests, gate it explicitly:

```python
if settings.ENVIRONMENT != "production" and not settings.RESEND_WEBHOOK_SECRET:
    payload = await request.json()
else:
    payload = _verify_resend_webhook(...)
```

### Step 2: Return correct status for oversized payloads

Current code returns a JSON success-like body:

```python
return {"status": "payload too large"}
```

Use:

```python
raise HTTPException(status_code=413, detail="Payload too large")
```

### Step 3: Add idempotency

Resend/Svix webhooks can retry. Store the `svix-id` value and avoid creating duplicate inbox items.

Option A: add column to `idea_inbox_items`:

```python
provider_event_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
```

Migration:

```python
op.add_column("idea_inbox_items", sa.Column("provider_event_id", sa.String(255), nullable=True))
op.create_unique_constraint("uq_idea_inbox_provider_event_id", "idea_inbox_items", ["provider_event_id"])
```

Then:

```python
event_id = request.headers.get("svix-id")
if event_id:
    existing = await db.execute(select(IdeaInbox).where(IdeaInbox.provider_event_id == event_id))
    if existing.scalar_one_or_none():
        return {"status": "duplicate"}
```

Option B: create a generic `webhook_events` table. Prefer this if more webhooks will need replay protection.

## Task 2: Protect Private Share Feedback Endpoints

### Files

- Modify `backend/app/routers/sharing.py`
- Modify `frontend/src/pages/SharedProject.tsx`
- Modify `frontend/src/components/sharing/CommentSection.tsx`
- Modify `frontend/src/components/sharing/StarRating.tsx`
- Modify `frontend/src/components/sharing/FeedbackPanel.tsx`

### Current Problem

The main shared project response is password-gated, but the following endpoints are not:

- `GET /sharing/public/{token}/comments`
- `POST /sharing/public/{token}/comments`
- `GET /sharing/public/{token}/ratings`
- `POST /sharing/public/{token}/ratings`

### Step 1: Add a viewer access token

After password verification succeeds, return a short-lived signed token:

```python
{
    "share_access_token": "...",
    ...shared_project_data
}
```

Use a server-side signer such as `itsdangerous.URLSafeTimedSerializer` or PyJWT with an internal secret. If adding a dependency is undesirable, use PyJWT already present:

```python
import jwt
from datetime import datetime, timedelta, timezone

def create_share_access_token(share_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(share_id),
            "scope": "share_view",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=6)).timestamp()),
        },
        settings.SHARE_ACCESS_SECRET,
        algorithm="HS256",
    )
```

Add `SHARE_ACCESS_SECRET` to config and env docs. If not configured, derive from an existing app secret only as a temporary fallback.

### Step 2: Require viewer access for private shares

Add helper:

```python
def _require_private_share_access(share: ProjectShare, authorization: str | None) -> None:
    if share.is_public or not share.password_hash:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Password verification required")
    token = authorization.removeprefix("Bearer ").strip()
    payload = jwt.decode(token, settings.SHARE_ACCESS_SECRET, algorithms=["HS256"])
    if payload.get("sub") != str(share.id) or payload.get("scope") != "share_view":
        raise HTTPException(status_code=403, detail="Password verification required")
```

Call this in:

- CSV export
- comments get/post
- ratings get/post

### Step 3: Pass token from frontend

In `SharedProject.tsx`, store `shareAccessToken` after verify.

Pass it to feedback components:

```tsx
<FeedbackPanel
  shareToken={token}
  shareAccessToken={shareAccessToken}
  blocks={data.blocks}
  allowFeedback={data.allow_feedback}
  allowRatings={data.allow_ratings}
/>
```

In `CommentSection` and `StarRating`, add:

```tsx
headers: {
  'Content-Type': 'application/json',
  ...(shareAccessToken ? { Authorization: `Bearer ${shareAccessToken}` } : {}),
}
```

### Step 4: Abuse controls

Add basic protections:

- Trim author/content.
- Reject blank author after trimming only if anonymous posting is disabled.
- Limit repeated ratings from the same email on the same share if email is provided.
- Consider simple IP-based throttling at Railway/proxy level later.

## Task 3: Centralize Entitlement Checks

### Files

- Modify `backend/app/services/entitlement_service.py`
- Modify `backend/app/routers/projects.py`
- Modify `backend/app/routers/templates.py`
- Modify `backend/app/routers/inbox.py`
- Modify `backend/app/routers/branching.py`
- Modify `backend/app/routers/library.py`
- Modify `backend/app/routers/prompts.py`
- Modify `backend/app/routers/market.py`
- Modify `backend/app/routers/sprints.py`
- Modify frontend pages to show upgrade UI on 403

### Step 1: Add reusable project creation guard

In `entitlement_service.py`:

```python
async def require_project_slot(user: User, db: AsyncSession) -> None:
    check = await check_project_limit(user, db)
    if not check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "project_limit_reached",
                "current": check["current"],
                "limit": check["limit"],
                "plan": check["plan"],
                "message": "Project limit reached. Upgrade your plan to create more projects.",
            },
        )
```

Keep the HTTPException out of pure service if you prefer domain exceptions, but keep one centralized function.

### Step 2: Use guard in every project creation path

Apply to:

- `backend/app/routers/projects.py` before blank project creation
- `backend/app/routers/templates.py` before creating template project
- `backend/app/routers/inbox.py` before promoting an inbox item
- `backend/app/routers/branching.py` before branch project creation
- `backend/app/routers/library.py` before import creates a project

### Step 3: Add counted feature checks

Replace `check_feature` with count-aware helpers:

```python
async def check_feature_usage(
    user: User,
    db: AsyncSession,
    feature: str,
) -> dict[str, Any]:
    limit = get_limits(user).get(feature)
    if limit is None:
        return {"allowed": True, "current": 0, "limit": None, "plan": user.account_type or "free"}

    if feature == "prompt_packages":
        current = await count_prompt_kits_for_user(user.id, db)
    elif feature == "market_analysis":
        current = await count_market_analyses_for_user(user.id, db)
    elif feature == "sprint_plans":
        current = await count_sprint_plans_for_user(user.id, db)
    else:
        current = 0

    return {"allowed": current < limit, "current": current, "limit": limit, "plan": user.account_type or "free"}
```

Counting choices:

- Prompt kits: count rows in `prompt_kits` joined through owned projects.
- Market analysis: count complete or generating rows for owned projects.
- Sprint plans: count complete or generating rows for owned projects.

### Step 4: Gate all paid feature endpoints

Apply counted checks to:

- `POST /projects/{project_id}/prompts/generate`
- `POST /projects/{project_id}/export/prompt-package`
- `POST /market/{project_id}/generate`
- `POST /sprints/{project_id}/generate`

Decide whether rewrite/regenerate should count as another usage. If yes, gate rewrite too.

### Step 5: Return structured 403 errors

Use consistent detail:

```json
{
  "code": "feature_limit_reached",
  "feature": "market_analysis",
  "current": 5,
  "limit": 5,
  "plan": "basic",
  "message": "Market analysis limit reached for this billing period."
}
```

If billing periods are not implemented, do not say "billing period." Use lifetime or current project count language.

### Step 6: Add frontend upgrade handling

For:

- Home project creation
- Template use
- Inbox promote
- Library import
- PromptKit generate/rewrite
- Market generate
- Sprint generate
- Export prompt package

Handle 403 responses:

```tsx
if (axios.isAxiosError(err) && err.response?.status === 403) {
  setUpgradeModalOpen(true)
  setEntitlementMessage(parseEntitlementMessage(err))
  return
}
```

Use the existing `UpgradeModal`.

## Task 4: Integration Token Handling

### Files

- Modify `backend/app/routers/integrations.py`
- Modify `backend/app/core/config.py`
- Modify `env.example`
- Add migration if needed

### Current Problem

Unconnected providers are marked `coming_soon`, but manual token creation/update endpoints still exist. Those endpoints now encrypt tokens, but they will raise a 500 if `INTEGRATION_TOKEN_KEY` is missing.

### Step 1: Decide scope

Choose one:

Option A: Fully de-scope integrations.

- Remove or disable POST/PATCH token endpoints for providers not implemented.
- Return 501 with a stable error code.

Option B: Keep manual token integration.

- Require `INTEGRATION_TOKEN_KEY` at application startup in production.
- Add admin docs for generating Fernet key.
- Add migration/one-time task for existing plaintext token rows.

### Step 2: Avoid leaking runtime exceptions

Wrap encryption errors:

```python
try:
    encrypted = encrypt_secret(payload.access_token)
except RuntimeError:
    raise HTTPException(status_code=503, detail="Integration credential storage is not configured")
```

### Step 3: Add env docs

`env.example` must include:

```env
INTEGRATION_TOKEN_KEY=
```

Add a comment:

```text
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Task 5: Verification

Run:

```powershell
cd frontend
npm.cmd run build
npm.cmd run lint
npm.cmd audit --json
```

Run backend syntax:

```powershell
cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python -m compileall app -q
```

After test dependencies exist:

```powershell
cd backend
python -m pytest tests -q
```

Manual API checks to add later:

- Password-protected share cannot fetch comments without viewer token.
- Password-verified share can fetch and post comments.
- Resend webhook verification accepts a known valid Svix signature fixture.
- Duplicate `svix-id` does not create a second inbox item.
- Free user cannot create a 4th project through templates/import/inbox/branch.

