"""
sharing_service.py — Project sharing helpers.
Manages share token generation, password verification, and data assembly.
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
from app.models.design_sheet import DesignSheet
from app.models.market_analysis import MarketAnalysis
from app.models.pipeline_node import PipelineNode
from app.models.project import Project
from app.models.project_share import ProjectShare


async def create_share(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    is_public: bool = True,
    password: str | None = None,
    expires_hours: int | None = None,
    allow_feedback: bool = True,
    allow_ratings: bool = True,
) -> ProjectShare:
    """Create a new share link for a project."""
    # Revoke any existing share first
    existing = await db.execute(
        select(ProjectShare).where(ProjectShare.project_id == project_id)
    )
    old = existing.scalar_one_or_none()
    if old:
        await db.delete(old)
        await db.flush()

    pw_hash = None
    if password:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    expires_at = None
    if expires_hours:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

    share = ProjectShare(
        project_id=project_id,
        share_token=secrets.token_urlsafe(32),
        is_public=is_public,
        password_hash=pw_hash,
        expires_at=expires_at,
        created_by=user_id,
        allow_feedback=allow_feedback,
        allow_ratings=allow_ratings,
    )
    db.add(share)
    await db.flush()
    return share


async def get_share_by_token(db: AsyncSession, token: str) -> ProjectShare | None:
    """Fetch a share by its token."""
    result = await db.execute(
        select(ProjectShare).where(ProjectShare.share_token == token)
    )
    return result.scalar_one_or_none()


async def get_share_by_project(db: AsyncSession, project_id: uuid.UUID) -> ProjectShare | None:
    """Fetch the active share for a project."""
    result = await db.execute(
        select(ProjectShare).where(ProjectShare.project_id == project_id)
    )
    return result.scalar_one_or_none()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a share password."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def get_shared_project_data(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Assemble full read-only project data for a shared view."""
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        return {}

    sheet_result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    sheet = sheet_result.scalar_one_or_none()

    blocks_result = await db.execute(
        select(Block).where(Block.project_id == project_id)
    )
    blocks = blocks_result.scalars().all()

    pipeline_result = await db.execute(
        select(PipelineNode).where(PipelineNode.project_id == project_id)
    )
    pipeline = pipeline_result.scalars().all()

    market_result = await db.execute(
        select(MarketAnalysis).where(MarketAnalysis.project_id == project_id)
    )
    market = market_result.scalar_one_or_none()

    return {
        "project": {
            "name": project.name,
            "description": project.description,
            "platform": project.platform,
            "audience": project.audience,
            "complexity": project.complexity,
            "tone": project.tone,
        },
        "design_sheet": {
            "problem": sheet.problem if sheet else None,
            "audience": sheet.audience if sheet else None,
            "mvp": sheet.mvp if sheet else None,
            "features": sheet.features if sheet else [],
            "tone": sheet.tone if sheet else None,
            "platform": sheet.platform if sheet else None,
            "tech_constraints": sheet.tech_constraints if sheet else None,
            "success_metric": sheet.success_metric if sheet else None,
            "confidence_score": sheet.confidence_score if sheet else 0,
        } if sheet else None,
        "blocks": [
            {
                "name": b.name,
                "description": b.description,
                "category": b.category,
                "priority": b.priority,
                "effort": b.effort,
                "is_mvp": b.is_mvp,
            }
            for b in blocks
        ],
        "pipeline": [
            {"layer": n.layer, "tool": n.selected_tool}
            for n in pipeline
        ],
        "market_analysis": {
            "status": market.status if market else None,
            "target_market": market.target_market if market else None,
            "competitive_landscape": market.competitive_landscape if market else None,
            "market_metrics": market.market_metrics if market else None,
            "revenue_projections": market.revenue_projections if market else None,
            "marketing_strategies": market.marketing_strategies if market else None,
        } if market else None,
    }


def export_blocks_as_csv(blocks: list[dict], project_name: str) -> str:
    """Export blocks as Linear-compatible CSV."""
    lines = ["Title,Description,Priority,Estimate,Label"]
    for b in blocks:
        title = b.get("name", "").replace('"', '""')
        desc = b.get("description", "").replace('"', '""')
        priority = "High" if b.get("is_mvp") else "Medium"
        estimate = b.get("effort", "M")
        label = "MVP" if b.get("is_mvp") else "V2"
        lines.append(f'"{title}","{desc}","{priority}","{estimate}","{label}"')
    return "\n".join(lines)
