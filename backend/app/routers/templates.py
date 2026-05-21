"""
templates.py — Project template CRUD for starter packs.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.models.design_sheet import DesignSheet
from app.models.project import Project
from app.models.project_template import ProjectTemplate
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.entitlement_service import require_project_slot

router = APIRouter(prefix="/templates", tags=["templates"])

# Maps template category slugs → concept_categories.seed.json IDs.
# Templates now use concept IDs directly (migration 024), but legacy
# slugs from migrations 017/018 are kept for backward compatibility.
CATEGORY_TO_CONCEPT: dict[str, str] = {
    # Identity mappings (concept category IDs used directly by new templates)
    "software_tech": "software_tech",
    "physical_product": "physical_product",
    "built_environment": "built_environment",
    "business_startup": "business_startup",
    "creative_writing": "creative_writing",
    "research_academic": "research_academic",
    "art_visual": "art_visual",
    "music_audio": "music_audio",
    "film_video": "film_video",
    "food_hospitality": "food_hospitality",
    "fashion_apparel": "fashion_apparel",
    "education_training": "education_training",
    "event_experience": "event_experience",
    "health_wellness": "health_wellness",
    "social_impact": "social_impact",
    "finance_investment": "finance_investment",
    # Legacy slugs (migrations 017/018)
    "saas": "software_tech",
    "mobile": "software_tech",
    "ecommerce": "business_startup",
    "content": "creative_writing",
    "ai_ml": "software_tech",
    "social": "software_tech",
    "creative": "art_visual",
    "developer": "software_tech",
    "marketplace": "business_startup",
    "general": "software_tech",
    "software": "software_tech",
    "business": "business_startup",
    "education": "education_training",
    "marketing": "business_startup",
    "personal": "creative_writing",
}


class TemplateRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    icon: str
    category: str
    concept_sheet: Optional[dict] = None
    is_system: bool

    class Config:
        from_attributes = True


class UseTemplatePayload(BaseModel):
    extra_description: Optional[str] = None
    ai_partner_style: Optional[str] = None


@router.get("", response_model=list[TemplateRead])
async def list_templates(db: AsyncSession = Depends(get_db)):
    """List all project templates (system + user-created)."""
    result = await db.execute(
        select(ProjectTemplate).order_by(ProjectTemplate.category, ProjectTemplate.name)
    )
    return result.scalars().all()


@router.post("/{template_id}/use")
async def use_template(
    template_id: uuid.UUID,
    payload: UseTemplatePayload = UseTemplatePayload(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project from a template, pre-populating design sheet from concept_sheet."""
    result = await db.execute(
        select(ProjectTemplate).where(ProjectTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await require_project_slot(current_user, db)

    # Build description from template + optional user detail
    description = template.description
    if payload.extra_description:
        description = f"{description}\n\n{payload.extra_description}"

    # Map template category to concept category for module pathway
    concept_category = CATEGORY_TO_CONCEPT.get(template.category, "software_tech")

    # Extract fields from template's concept_sheet
    cs = template.concept_sheet or {}

    project = Project(
        name=f"{template.name} Project",
        description=description,
        user_id=current_user.id,
        platform=cs.get("platform", "custom"),
        ai_partner_style=payload.ai_partner_style or "strategist",
        primary_category=concept_category,
    )
    db.add(project)
    await db.flush()

    # Pre-populate design sheet from the template's concept_sheet
    sheet = DesignSheet(
        project_id=project.id,
        platform=cs.get("platform"),
        tone=cs.get("tone"),
        tech_constraints=cs.get("tech_constraints"),
        success_metric=cs.get("success_metric"),
        problem=cs.get("problem"),
        audience=cs.get("audience"),
        mvp=cs.get("mvp"),
        features=cs.get("features"),
        confidence_score=cs.get("confidence_score", 20),
    )
    db.add(sheet)
    await db.flush()

    return {
        "project_id": str(project.id),
        "name": project.name,
        "template_name": template.name,
        "category": concept_category,
    }
