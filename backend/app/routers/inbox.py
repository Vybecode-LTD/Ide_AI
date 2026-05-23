"""
inbox.py — Idea Inbox router. Lets users capture quick ideas (manual or email),
list them, promote to projects, and delete. Also exposes a /stream SSE endpoint
that pushes realtime events (added/promoted/deleted) via Redis pub/sub.
"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.models.idea_inbox import IdeaInbox
from app.models.project import Project
from app.models.user import User
from app.routers.auth import get_current_user
from app.services import inbox_pubsub
from app.services.entitlement_service import require_project_slot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inbox", tags=["inbox"])


# ── Schemas ──

class InboxItemCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: Optional[str] = None

class InboxItemRead(BaseModel):
    id: uuid.UUID
    subject: str
    body: Optional[str] = None
    source: str
    sender_email: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    created_at: str

    class Config:
        from_attributes = True

class InboxPromote(BaseModel):
    """Promote an inbox item to a full project."""
    name: Optional[str] = Field(None, max_length=200)
    ai_partner_style: Optional[str] = Field(None, max_length=30)


# ── Endpoints ──

@router.get("", response_model=list[InboxItemRead])
async def list_inbox(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all inbox items for the current user, newest first."""
    result = await db.execute(
        select(IdeaInbox)
        .where(IdeaInbox.user_id == current_user.id)
        .order_by(IdeaInbox.created_at.desc())
    )
    items = result.scalars().all()
    return [
        InboxItemRead(
            id=item.id,
            subject=item.subject,
            body=item.body,
            source=item.source,
            sender_email=item.sender_email,
            project_id=item.project_id,
            created_at=item.created_at.isoformat(),
        )
        for item in items
    ]


@router.post("", response_model=InboxItemRead, status_code=status.HTTP_201_CREATED)
async def create_inbox_item(
    payload: InboxItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually add an idea to the inbox."""
    item = IdeaInbox(
        user_id=current_user.id,
        subject=payload.subject,
        body=payload.body,
        source="manual",
    )
    db.add(item)
    await db.flush()
    response = InboxItemRead(
        id=item.id,
        subject=item.subject,
        body=item.body,
        source=item.source,
        sender_email=item.sender_email,
        project_id=item.project_id,
        created_at=item.created_at.isoformat(),
    )
    # Notify any open /inbox/stream subscribers (best-effort, no-op without Redis)
    await inbox_pubsub.publish_event(
        current_user.id,
        {"type": "added", "id": str(item.id), "subject": item.subject},
    )
    return response


@router.post("/{item_id}/promote", status_code=status.HTTP_200_OK)
async def promote_to_project(
    item_id: uuid.UUID,
    payload: InboxPromote,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Promote an inbox item to a full project."""
    result = await db.execute(
        select(IdeaInbox).where(IdeaInbox.id == item_id, IdeaInbox.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    if item.project_id:
        raise HTTPException(status_code=400, detail="Already promoted to a project")

    await require_project_slot(current_user, db)

    # Validate partner style (or fall back to default)
    partner_style = "strategist"
    if payload.ai_partner_style:
        from app.services.partner_style_service import validate_partner_style
        try:
            partner_style = validate_partner_style(payload.ai_partner_style)
        except ValueError:
            partner_style = "strategist"

    project = Project(
        name=payload.name or item.subject[:200],
        description=item.body or item.subject,
        user_id=current_user.id,
        platform="custom",
        audience="consumers",
        complexity="medium",
        tone="casual",
        pathway_id="software_product",
        ai_partner_style=partner_style,
    )
    db.add(project)
    await db.flush()

    item.project_id = project.id
    await db.flush()

    await inbox_pubsub.publish_event(
        current_user.id,
        {"type": "promoted", "id": str(item.id), "project_id": str(project.id)},
    )

    return {"project_id": str(project.id), "name": project.name}


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inbox_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an inbox item."""
    result = await db.execute(
        select(IdeaInbox).where(IdeaInbox.id == item_id, IdeaInbox.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    await db.delete(item)
    await inbox_pubsub.publish_event(
        current_user.id,
        {"type": "deleted", "id": str(item_id)},
    )


@router.get("/count")
async def inbox_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unread inbox count (items not promoted to projects)."""
    result = await db.execute(
        select(sa_func.count(IdeaInbox.id))
        .where(IdeaInbox.user_id == current_user.id, IdeaInbox.project_id.is_(None))
    )
    count = result.scalar() or 0
    return {"count": count}


# ── Realtime stream ─────────────────────────────────────────────────


@router.get("/stream")
async def inbox_stream(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE stream of inbox events for the current user.

    Yields one ``event: hello`` with the initial count, then pushes one
    ``event: update`` per inbox mutation (added / promoted / deleted) as
    they happen.

    Returns 503 if Redis is not configured — the frontend falls back to
    polling in that case.
    """
    if not inbox_pubsub.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Realtime inbox is not configured (REDIS_URL missing)",
        )

    # Initial count snapshot so the client doesn't have to fetch separately
    count_result = await db.execute(
        select(sa_func.count(IdeaInbox.id)).where(
            IdeaInbox.user_id == current_user.id,
            IdeaInbox.project_id.is_(None),
        )
    )
    initial_count = count_result.scalar() or 0

    user_id = current_user.id  # capture before request scope closes

    async def event_stream():
        # Initial hello so the client knows the channel is open + has the current count
        yield f"event: hello\ndata: {json.dumps({'count': initial_count})}\n\n"

        try:
            subscription = inbox_pubsub.subscribe(user_id)
            async for event in subscription:
                if await request.is_disconnected():
                    break
                payload = json.dumps(event)
                yield f"event: update\ndata: {payload}\n\n"
        except asyncio.CancelledError:
            # Client disconnected — let the generator end cleanly
            raise
        except Exception as exc:
            logger.warning("inbox stream errored for user %s: %s", user_id, exc)
            yield f"event: error\ndata: {json.dumps({'message': 'stream interrupted'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Caddy/nginx buffering
        },
    )
