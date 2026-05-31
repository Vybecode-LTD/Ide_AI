"""
integrations.py — External tool integrations (Notion, Trello, Linear, Figma, Google Docs, Airtable).
Provides CRUD for integration credentials and export endpoints.

Notion is the first live integration: full 3-legged OAuth + a "push design kit
to a Notion page" action. The other providers remain ``coming_soon`` stubs.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.encryption import decrypt_secret, encrypt_secret
from app.models.external_integration import ExternalIntegration
from app.models.user import User
from app.routers.auth import get_current_user
from app.services import notion_service
from app.services.artifact_context_service import build_artifact_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])

SUPPORTED_PROVIDERS = {"notion", "trello", "linear", "figma", "google_docs", "airtable"}

# Providers that are actually wired up (not coming_soon).
LIVE_PROVIDERS = {"notion"}


class IntegrationCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    access_token: Optional[str] = None
    config: Optional[dict] = None

class IntegrationRead(BaseModel):
    id: uuid.UUID
    provider: str
    enabled: bool
    has_token: bool
    config: Optional[dict] = None
    created_at: str

class IntegrationUpdate(BaseModel):
    access_token: Optional[str] = None
    config: Optional[dict] = None
    enabled: Optional[bool] = None


@router.get("")
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all integrations for the current user."""
    result = await db.execute(
        select(ExternalIntegration)
        .where(ExternalIntegration.user_id == current_user.id)
        .order_by(ExternalIntegration.provider)
    )
    integrations = result.scalars().all()

    # Also include unconnected providers
    connected = {i.provider for i in integrations}
    items = []
    for i in integrations:
        items.append({
            "id": str(i.id),
            "provider": i.provider,
            "enabled": i.enabled,
            "has_token": bool(i.access_token),
            "config": i.config,
            "created_at": i.created_at.isoformat(),
        })
    for provider in sorted(SUPPORTED_PROVIDERS - connected):
        # Live providers (Notion) advertise availability + whether the server
        # has the OAuth env vars set; everything else is still coming_soon.
        if provider in LIVE_PROVIDERS:
            items.append({
                "id": None,
                "provider": provider,
                "enabled": False,
                "has_token": False,
                "config": None,
                "created_at": None,
                "status": "available",
                "configured": notion_service.is_configured() if provider == "notion" else False,
            })
        else:
            items.append({
                "id": None,
                "provider": provider,
                "enabled": False,
                "has_token": False,
                "config": None,
                "created_at": None,
                "status": "coming_soon",
            })
    return items


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_integration(
    payload: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect a new external tool integration."""
    if payload.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider. Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}",
        )

    # Check if already exists
    result = await db.execute(
        select(ExternalIntegration).where(
            ExternalIntegration.user_id == current_user.id,
            ExternalIntegration.provider == payload.provider,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Integration already connected")

    try:
        encrypted_token = encrypt_secret(payload.access_token)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Integration credential storage is not configured")

    integration = ExternalIntegration(
        user_id=current_user.id,
        provider=payload.provider,
        access_token=encrypted_token,
        config=payload.config or {},
    )
    db.add(integration)
    await db.flush()

    return {
        "id": str(integration.id),
        "provider": integration.provider,
        "enabled": integration.enabled,
    }


@router.patch("/{integration_id}")
async def update_integration(
    integration_id: uuid.UUID,
    payload: IntegrationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update integration settings or credentials."""
    result = await db.execute(
        select(ExternalIntegration).where(
            ExternalIntegration.id == integration_id,
            ExternalIntegration.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    if payload.access_token is not None:
        try:
            integration.access_token = encrypt_secret(payload.access_token)
        except RuntimeError:
            raise HTTPException(status_code=503, detail="Integration credential storage is not configured")
    if payload.config is not None:
        integration.config = payload.config
    if payload.enabled is not None:
        integration.enabled = payload.enabled

    await db.flush()
    return {"id": str(integration.id), "provider": integration.provider, "enabled": integration.enabled}


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect an external tool integration."""
    result = await db.execute(
        select(ExternalIntegration).where(
            ExternalIntegration.id == integration_id,
            ExternalIntegration.user_id == current_user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    await db.delete(integration)


# ── Notion OAuth + push ──────────────────────────────────────────────────────
#
# Flow: the SPA calls POST /notion/authorize (authenticated) to get a Notion
# authorize URL carrying a signed `state`. The browser bounces to Notion, the
# user approves, Notion redirects to GET /notion/callback (public — no Clerk
# header on a browser redirect, so auth rides in the verified `state`). We
# exchange the code for a token, store it Fernet-encrypted, and redirect back
# to the SPA. POST /notion/push/{project_id} renders the design kit into a
# Notion page under a parent the user picked.

_OAUTH_STATE_SCOPE = "notion_oauth"
_OAUTH_STATE_TTL = timedelta(minutes=10)


def _oauth_state_secret() -> str:
    """Signing secret for the OAuth state token.

    Reuses the same fallback chain as the share-viewer tokens so we don't add
    yet another required secret: SHARE_ACCESS_SECRET, then CLERK_SECRET_KEY.
    """
    secret = settings.SHARE_ACCESS_SECRET or settings.CLERK_SECRET_KEY
    if not secret:
        raise RuntimeError("SHARE_ACCESS_SECRET (or CLERK_SECRET_KEY as fallback) must be set")
    return secret


def _mint_oauth_state(user_id: uuid.UUID) -> str:
    """Sign a short-lived state token binding the OAuth round-trip to a user."""
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "scope": _OAUTH_STATE_SCOPE,
            "jti": uuid.uuid4().hex,
            "iat": int(now.timestamp()),
            "exp": int((now + _OAUTH_STATE_TTL).timestamp()),
        },
        _oauth_state_secret(),
        algorithm="HS256",
    )


def _verify_oauth_state(state: str) -> uuid.UUID:
    """Verify a state token and return the bound user id. Raises ValueError."""
    try:
        payload = jwt.decode(state, _oauth_state_secret(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise ValueError(f"invalid state token: {exc}")
    if payload.get("scope") != _OAUTH_STATE_SCOPE:
        raise ValueError("wrong state scope")
    sub = payload.get("sub")
    if not sub:
        raise ValueError("state missing subject")
    try:
        return uuid.UUID(sub)
    except (ValueError, TypeError):
        raise ValueError("state subject is not a uuid")


def _settings_redirect(status_value: str) -> RedirectResponse:
    """Redirect back to the SPA settings page with a ?notion=<status> flag."""
    base = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(url=f"{base}/settings?notion={status_value}")


class NotionPushRequest(BaseModel):
    parent_page_id: Optional[str] = Field(default=None, max_length=100)


@router.post("/notion/authorize")
async def notion_authorize(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the Notion authorize URL (with a signed state) for the SPA to open."""
    if not notion_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notion integration is not configured on the server",
        )
    try:
        state = _mint_oauth_state(current_user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"authorize_url": notion_service.build_authorize_url(state)}


@router.get("/notion/callback")
async def notion_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """OAuth redirect target. Public — auth rides in the verified ``state``.

    Always redirects back to the SPA (never returns JSON) so the user lands
    somewhere sensible whether the connection succeeded or failed.
    """
    if error or not code or not state:
        logger.info("Notion callback rejected: error=%s code=%s", error, bool(code))
        return _settings_redirect("error")

    if not notion_service.is_configured():
        return _settings_redirect("error")

    try:
        user_id = _verify_oauth_state(state)
    except ValueError as exc:
        logger.warning("Notion callback bad state: %s", exc)
        return _settings_redirect("error")

    # Confirm the user still exists.
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        return _settings_redirect("error")

    try:
        token_payload = await notion_service.exchange_code_for_token(code)
    except Exception as exc:  # noqa: BLE001 — surface as a clean redirect
        logger.error("Notion token exchange failed: %s", exc)
        return _settings_redirect("error")

    access_token = token_payload.get("access_token")
    if not access_token:
        return _settings_redirect("error")

    try:
        encrypted = encrypt_secret(access_token)
    except RuntimeError:
        logger.error("Cannot store Notion token — INTEGRATION_TOKEN_KEY is unset")
        return _settings_redirect("error")

    config = {
        "workspace_id": token_payload.get("workspace_id"),
        "workspace_name": token_payload.get("workspace_name"),
        "workspace_icon": token_payload.get("workspace_icon"),
        "bot_id": token_payload.get("bot_id"),
    }

    # Upsert the (user, notion) integration row.
    existing = (
        await db.execute(
            select(ExternalIntegration).where(
                ExternalIntegration.user_id == user_id,
                ExternalIntegration.provider == "notion",
            )
        )
    ).scalar_one_or_none()

    if existing:
        existing.access_token = encrypted
        existing.config = config
        existing.enabled = True
    else:
        db.add(
            ExternalIntegration(
                user_id=user_id,
                provider="notion",
                access_token=encrypted,
                config=config,
                enabled=True,
            )
        )
    await db.commit()

    return _settings_redirect("connected")


async def _get_notion_token(db: AsyncSession, user_id: uuid.UUID) -> tuple[ExternalIntegration, str]:
    """Load the user's Notion integration and decrypt its token.

    Raises 404 if not connected, 503 if the stored token can't be decrypted
    (e.g. INTEGRATION_TOKEN_KEY rotated).
    """
    integration = (
        await db.execute(
            select(ExternalIntegration).where(
                ExternalIntegration.user_id == user_id,
                ExternalIntegration.provider == "notion",
            )
        )
    ).scalar_one_or_none()
    if not integration or not integration.access_token:
        raise HTTPException(status_code=404, detail="Notion is not connected")
    token = decrypt_secret(integration.access_token)
    if not token:
        raise HTTPException(status_code=503, detail="Stored Notion token could not be read; reconnect Notion")
    return integration, token


@router.get("/notion/pages")
async def notion_pages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List Notion pages the integration can write to (for the parent picker)."""
    _, token = await _get_notion_token(db, current_user.id)
    try:
        pages = await notion_service.list_accessible_pages(token)
    except Exception as exc:  # noqa: BLE001
        logger.error("Notion page listing failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not list Notion pages")
    return {"pages": pages}


@router.post("/notion/push/{project_id}")
async def notion_push(
    project_id: uuid.UUID,
    payload: NotionPushRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Render a project's design kit into a new Notion page.

    The parent page is taken from the request body, falling back to the last
    one stored in the integration config. Ownership is enforced by
    ``build_artifact_context`` (raises 404 for a project the user doesn't own).
    """
    integration, token = await _get_notion_token(db, current_user.id)

    parent_page_id = payload.parent_page_id or (integration.config or {}).get("parent_page_id")
    if not parent_page_id:
        raise HTTPException(status_code=400, detail="A Notion parent page is required")

    # Build the unified context (also performs the ownership check → 404).
    context = await build_artifact_context(db, project_id, current_user.id)

    blocks = notion_service.render_design_kit_blocks(context)
    title = context.get("project_name") or "Design Kit"

    try:
        result = await notion_service.create_design_kit_page(token, parent_page_id, title, blocks)
    except Exception as exc:  # noqa: BLE001
        logger.error("Notion page creation failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not create the Notion page")

    # Remember the parent page so future pushes can default to it.
    cfg = dict(integration.config or {})
    cfg["parent_page_id"] = parent_page_id
    integration.config = cfg
    await db.commit()

    return {"status": "pushed", "page_id": result.get("id"), "url": result.get("url")}


# ── Provider-specific export helpers ──

PROVIDER_META = {
    "notion": {"name": "Notion", "icon": "📝", "description": "Export blocks and design sheets to Notion pages"},
    "trello": {"name": "Trello", "icon": "📋", "description": "Create Trello cards from project blocks and sprints"},
    "linear": {"name": "Linear", "icon": "⚡", "description": "Sync project blocks as Linear issues"},
    "figma": {"name": "Figma", "icon": "🎨", "description": "Push mood boards and design tokens to Figma"},
    "google_docs": {"name": "Google Docs", "icon": "📄", "description": "Export concept sheets and reports to Google Docs"},
    "airtable": {"name": "Airtable", "icon": "📊", "description": "Sync project data to Airtable bases"},
}

@router.get("/providers")
async def list_providers():
    """List all supported integration providers with metadata."""
    return [{"id": k, **v} for k, v in PROVIDER_META.items()]
