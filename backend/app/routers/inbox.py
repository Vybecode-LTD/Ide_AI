"""
inbox.py — Idea Inbox router. Lets users capture quick ideas (manual or email),
list them, promote to projects, and delete.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
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
    return InboxItemRead(
        id=item.id,
        subject=item.subject,
        body=item.body,
        source=item.source,
        sender_email=item.sender_email,
        project_id=item.project_id,
        created_at=item.created_at.isoformat(),
    )


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

    project = Project(
        name=payload.name or item.subject[:200],
        description=item.body or item.subject,
        user_id=current_user.id,
        platform="custom",
        audience="consumers",
        complexity="medium",
        tone="casual",
        pathway_id="software_product",
        ai_partner_style="strategist",
    )
    db.add(project)
    await db.flush()

    item.project_id = project.id
    await db.flush()

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
