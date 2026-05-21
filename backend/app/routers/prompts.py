"""
prompts.py — Prompt kit router. Generation and management of platform-specific prompts.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.block import Block
from app.models.design_sheet import DesignSheet
from app.models.project import Project
from app.models.prompt_kit import PromptKit
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.prompt_kit import PromptKitGenerate, PromptKitRead
from app.services.entitlement_service import require_feature_usage
from app.services.prompt_kit_service import generate_prompt_kit

router = APIRouter(prefix="/projects/{project_id}/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptKitRead])
async def list_prompt_kits(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all prompt kits for a project."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(PromptKit)
        .where(PromptKit.project_id == project_id)
        .order_by(PromptKit.created_at.desc())
    )
    return result.scalars().all()


@router.post("/generate", response_model=PromptKitRead, status_code=status.HTTP_201_CREATED)
async def create_prompt_kit(
    project_id: uuid.UUID,
    payload: PromptKitGenerate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a platform-specific prompt kit."""
    await require_feature_usage(current_user, db, "prompt_packages")

    # Verify project
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Get design sheet
    sheet_result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    sheet = sheet_result.scalar_one_or_none()
    if not sheet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design sheet not found")

    # Get blocks
    blocks_result = await db.execute(
        select(Block).where(Block.project_id == project_id).order_by(Block.order)
    )
    blocks = blocks_result.scalars().all()

    # Generate prompt kit
    content = await generate_prompt_kit(sheet, list(blocks), payload.platform)

    # Get next version number
    version_result = await db.execute(
        select(PromptKit.version)
        .where(PromptKit.project_id == project_id, PromptKit.platform == payload.platform)
        .order_by(PromptKit.version.desc())
        .limit(1)
    )
    max_version = version_result.scalar() or 0

    kit = PromptKit(
        project_id=project_id,
        platform=payload.platform,
        content=content,
        version=max_version + 1,
    )
    db.add(kit)
    await db.flush()
    return kit


@router.post("/{prompt_id}/rewrite", response_model=PromptKitRead)
async def rewrite_prompt(
    project_id: uuid.UUID,
    prompt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate a prompt kit with a new version."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(PromptKit).where(PromptKit.id == prompt_id, PromptKit.project_id == project_id)
    )
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt kit not found")

    # Get design sheet and blocks for regeneration
    sheet_result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    sheet = sheet_result.scalar_one_or_none()
    if not sheet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design sheet not found")
    blocks_result = await db.execute(
        select(Block).where(Block.project_id == project_id).order_by(Block.order)
    )
    blocks = blocks_result.scalars().all()

    content = await generate_prompt_kit(sheet, list(blocks), existing.platform)

    kit = PromptKit(
        project_id=project_id,
        platform=existing.platform,
        content=content,
        version=existing.version + 1,
    )
    db.add(kit)
    await db.flush()
    return kit
