"""
module_pathway.py — API endpoints for the modular dynamic pathway system.
Handles categorization, pathway assembly, review, editing, and locking.
"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.design_sheet import DesignSheet
from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.models.project import Project
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.module_pathway import (
    CategorizeResponse,
    PathwayAssembleResponse,
    PathwayRead,
    PathwayUpdate,
)
from app.services.categorization_service import categorize_project
from app.services.modular_pathway_service import (
    assemble_pathway,
    get_lite_deep_defaults,
)

router = APIRouter(prefix="/projects", tags=["module-pathway"])


async def _get_project(
    project_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Project:
    """Helper to fetch and verify project ownership."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_concept_sheet(project_id: uuid.UUID, db: AsyncSession) -> dict:
    """Load concept sheet as a dict for services."""
    result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    sheet = result.scalar_one_or_none()
    if not sheet:
        return {}
    data = {
        "problem": sheet.problem,
        "audience": sheet.audience,
        "mvp": sheet.mvp,
        "tone": sheet.tone,
        "platform": sheet.platform,
        "tech_constraints": sheet.tech_constraints,
        "success_metric": sheet.success_metric,
        "features": sheet.features or [],
        "fields_data": sheet.fields_data or {},
        "confidence_score": sheet.confidence_score,
    }
    return {k: v for k, v in data.items() if v is not None}


# ── Categorization ───────────────────────────────────────────────────

@router.post("/{project_id}/categorize", response_model=CategorizeResponse)
async def categorize_project_endpoint(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-categorize a project based on its completed concept sheet.

    If the project already has a primary_category (e.g. set by a template),
    skip AI categorization and return the existing category immediately.
    """
    project = await _get_project(project_id, current_user, db)

    # If category already set (from template or prior categorization), skip AI
    if project.primary_category:
        return {
            "primary_category": project.primary_category,
            "secondary_category": project.secondary_category,
            "confidence": 1.0,
            "reasoning": "Category already set from template or prior classification.",
        }

    concept_sheet = await _get_concept_sheet(project_id, db)

    result = await categorize_project(
        concept_sheet,
        project_name=project.name or "",
        project_description=project.description or "",
    )

    # Persist categories on the project
    project.primary_category = result["primary_category"]
    project.secondary_category = result.get("secondary_category")
    await db.commit()
    await db.refresh(project)

    return result


# ── Pathway Assembly ─────────────────────────────────────────────────

@router.post("/{project_id}/pathway/assemble", response_model=PathwayAssembleResponse)
async def assemble_pathway_endpoint(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assemble a module pathway: base stack + enrichment pass."""
    project = await _get_project(project_id, current_user, db)

    if not project.primary_category:
        raise HTTPException(
            status_code=400,
            detail="Project must be categorized first. Call POST /categorize.",
        )

    concept_sheet = await _get_concept_sheet(project_id, db)
    result = assemble_pathway(
        concept_sheet,
        project.primary_category,
        project.secondary_category,
    )

    # Persist the pathway
    module_ids = [m["module_id"] for m in result["modules"]]
    lite_deep = get_lite_deep_defaults(module_ids)

    existing = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
    )
    pathway = existing.scalar_one_or_none()

    if pathway:
        pathway.modules = module_ids
        pathway.lite_deep_settings = lite_deep
        pathway.status = "pending"
    else:
        pathway = ModulePathway(
            project_id=project_id,
            modules=module_ids,
            lite_deep_settings=lite_deep,
            status="pending",
        )
        db.add(pathway)

    await db.commit()

    return result


# ── Pathway CRUD ─────────────────────────────────────────────────────

@router.get("/{project_id}/pathway", response_model=PathwayRead)
async def get_pathway(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current pathway state for a project."""
    await _get_project(project_id, current_user, db)

    result = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
    )
    pathway = result.scalar_one_or_none()
    if not pathway:
        raise HTTPException(status_code=404, detail="No pathway assembled yet")
    return pathway


@router.patch("/{project_id}/pathway", response_model=PathwayRead)
async def update_pathway(
    project_id: uuid.UUID,
    payload: PathwayUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update module order, additions, removals, and lite/deep settings."""
    project = await _get_project(project_id, current_user, db)
    if project.pathway_locked:
        raise HTTPException(status_code=400, detail="Pathway is locked and cannot be edited")

    result = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
    )
    pathway = result.scalar_one_or_none()
    if not pathway:
        raise HTTPException(status_code=404, detail="No pathway assembled yet")

    pathway.modules = payload.modules
    if payload.lite_deep_settings:
        pathway.lite_deep_settings = payload.lite_deep_settings

    await db.commit()
    await db.refresh(pathway)
    return pathway


@router.post("/{project_id}/pathway/lock", response_model=PathwayRead)
async def lock_pathway(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lock the pathway and begin execution."""
    project = await _get_project(project_id, current_user, db)
    if project.pathway_locked:
        raise HTTPException(status_code=400, detail="Pathway already locked")

    result = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
    )
    pathway = result.scalar_one_or_none()
    if not pathway:
        raise HTTPException(status_code=404, detail="No pathway assembled yet")

    project.pathway_locked = True
    pathway.status = "active"
    await db.commit()
    await db.refresh(pathway)

    return pathway


@router.get("/{project_id}/design-kit")
async def get_design_kit(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the full design kit: decorated modules with field schemas + current values.

    Only valid for v2 projects. Returns 409 for v1 projects.
    """
    from app.services.discovery_service import load_decorated_pathway_modules

    project = await _get_project(project_id, current_user, db)
    if getattr(project, "flow_version", "v1") != "v2":
        raise HTTPException(status_code=409, detail="Design kit only available for v2 projects")

    modules = await load_decorated_pathway_modules(db, project_id)
    if not modules:
        raise HTTPException(status_code=404, detail="No pathway modules assembled")

    # Fetch all module responses for this project
    resp_result = await db.execute(
        select(ModuleResponse).where(ModuleResponse.project_id == project_id)
    )
    by_mid = {r.module_id: r for r in resp_result.scalars().all()}

    # Merge field values into each module
    kit_modules = []
    for mod in modules:
        mid = mod["module_id"]
        resp = by_mid.get(mid)
        kit_modules.append({
            **mod,
            "responses": resp.responses if resp else {},
            "status": resp.status if resp else "pending",
        })

    return {
        "project_id": str(project_id),
        "project_name": project.name,
        "modules": kit_modules,
    }
