"""
projects.py — Project CRUD router. Manages user project workspaces.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.module_pathway import ModulePathway
from app.models.project import Project
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import modular_pathway_service
from app.services.entitlement_service import require_project_slot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects for the current user."""
    result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.updated_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    await require_project_slot(current_user, db)

    project = Project(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        platform=payload.platform,
        audience=payload.audience,
        complexity=payload.complexity,
        tone=payload.tone,
        accent_color=payload.accent_color or "#00E5FF",
        pathway_id=payload.pathway_id,
        ai_partner_style=payload.ai_partner_style,
        primary_category=payload.primary_category,
        secondary_category=payload.secondary_category,
    )
    db.add(project)
    await db.flush()

    # v2 flow: assemble the module pathway UP FRONT so discovery can target
    # all module fields from the first turn. Skipped for legacy v1 projects
    # (no pre-assembly — they still use Discovery → PathwayReview → Execute).
    #
    # Note: module_pathways.modules stores ONLY module-id strings to match the
    # PathwayRead schema and the existing modules.py/PathwayExecute consumers.
    # The unified-discovery prompt builder decorates these IDs into full
    # module entries (with fields/labels) on read.
    #
    # Critical: if assembly is skipped (no primary_category) or yields zero
    # modules (unknown category, library missing) or throws, we MUST downgrade
    # `flow_version` to "v1". Otherwise the frontend reads "v2" from
    # `GET /projects/{id}`, renders ProgressPanel, never receives a
    # field_update (the v2 discovery branch requires a pathway row), and the
    # Proceed button never appears — leaving the user stranded. This is audit
    # finding H1.
    pathway_created = False
    if project.flow_version == "v2" and project.primary_category:
        try:
            assembled = modular_pathway_service.assemble_pathway_from_creation_inputs(
                description=project.description,
                primary_category=project.primary_category,
                secondary_category=project.secondary_category,
                platform=project.platform,
                audience=project.audience,
                tone=project.tone,
            )
            module_entries = assembled.get("modules") or []
            module_ids = [m["module_id"] for m in module_entries if m.get("module_id")]
            if module_ids:
                pathway = ModulePathway(
                    project_id=project.id,
                    modules=module_ids,
                    lite_deep_settings=modular_pathway_service.get_lite_deep_defaults(module_ids),
                    status="active",
                )
                db.add(pathway)
                await db.flush()
                pathway_created = True
            else:
                logger.warning(
                    "Up-front pathway assembly returned 0 modules for project %s; falling back to v1",
                    project.id,
                )
        except Exception as exc:
            logger.warning(
                "Up-front pathway assembly failed for project %s: %s; falling back to v1",
                project.id, exc,
            )

    # H1 fix: downgrade orphan v2 projects to v1 so the frontend renders the
    # legacy DesignSheetPanel + confidence-gated Proceed button instead of an
    # empty ProgressPanel.
    if project.flow_version == "v2" and not pathway_created:
        project.flow_version = "v1"
        await db.flush()

    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific project by ID."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project and all related data."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    await db.delete(project)
    await db.flush()
