"""
integrations.py — External tool integrations (Notion, Trello, Linear, Figma, Google Docs, Airtable).
Provides CRUD for integration credentials and export endpoints.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.encryption import encrypt_secret
from app.models.external_integration import ExternalIntegration
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/integrations", tags=["integrations"])

SUPPORTED_PROVIDERS = {"notion", "trello", "linear", "figma", "google_docs", "airtable"}


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
