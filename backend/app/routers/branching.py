"""
branching.py — Concept branching (git-like fork for ideas).
Creates a copy of a project so users can explore alternative directions.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.models.block import Block
from app.models.concept_branch import ConceptBranch
from app.models.design_sheet import DesignSheet
from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.models.pipeline_node import PipelineNode
from app.models.project import Project
from app.models.prompt_kit import PromptKit
from app.models.session import DiscoverySession
from app.models.sprint_plan import SprintPlan
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.library_service import _gather_project_state

router = APIRouter(prefix="/branching", tags=["branching"])


class BranchCreate(BaseModel):
    branch_name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class BranchRead(BaseModel):
    id: uuid.UUID
    parent_project_id: uuid.UUID
    branch_project_id: uuid.UUID
    branch_name: str
    description: Optional[str] = None
    created_at: str


async def _copy_child_records(
    state: dict,
    target_project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Deep-copy child records from a gathered project state onto a target project."""
    # Design sheet
    sheet_data = state.get("design_sheet")
    if sheet_data:
        db.add(DesignSheet(
            project_id=target_project_id,
            problem=sheet_data.get("problem"),
            audience=sheet_data.get("audience"),
            mvp=sheet_data.get("mvp"),
            features=sheet_data.get("features"),
            tone=sheet_data.get("tone"),
            platform=sheet_data.get("platform"),
            tech_constraints=sheet_data.get("tech_constraints"),
            success_metric=sheet_data.get("success_metric"),
            confidence_score=sheet_data.get("confidence_score", 0),
        ))

    # Discovery sessions
    for s in state.get("discovery_sessions", []):
        db.add(DiscoverySession(
            project_id=target_project_id,
            status=s.get("status", "completed"),
            stage=s.get("stage", "complete"),
            messages=s.get("messages"),
        ))

    # Blocks
    for b in state.get("blocks", []):
        db.add(Block(
            project_id=target_project_id,
            name=b.get("name", "Untitled"),
            description=b.get("description"),
            category=b.get("category", "feature"),
            priority=b.get("priority", "mvp"),
            effort=b.get("effort", "M"),
            order=b.get("order", 0),
            is_mvp=b.get("is_mvp", True),
        ))

    # Pipeline nodes
    for n in state.get("pipeline", []):
        db.add(PipelineNode(
            project_id=target_project_id,
            layer=n.get("layer", ""),
            selected_tool=n.get("selected_tool", ""),
            config=n.get("config"),
        ))

    # Prompt kits
    for pk in state.get("prompt_kits", []):
        db.add(PromptKit(
            project_id=target_project_id,
            platform=pk.get("platform", "generic"),
            content=pk.get("content", ""),
            version=pk.get("version", 1),
        ))

    # Sprint plan
    sprint_data = state.get("sprint_plan")
    if sprint_data:
        db.add(SprintPlan(
            project_id=target_project_id,
            user_id=user_id,
            milestones=sprint_data.get("milestones"),
            sprints=sprint_data.get("sprints"),
            timeline=sprint_data.get("timeline"),
            status=sprint_data.get("status", "complete"),
        ))

    # Module pathway
    mp_data = state.get("module_pathway")
    if mp_data:
        db.add(ModulePathway(
            project_id=target_project_id,
            modules=mp_data.get("modules", []),
            lite_deep_settings=mp_data.get("lite_deep_settings", {}),
            status=mp_data.get("status", "pending"),
        ))

    # Module responses
    for mr in state.get("module_responses", []):
        db.add(ModuleResponse(
            project_id=target_project_id,
            module_id=mr.get("module_id", ""),
            responses=mr.get("responses", {}),
            status=mr.get("status", "pending"),
        ))

    await db.flush()


@router.post("/{project_id}/branch", status_code=status.HTTP_201_CREATED)
async def create_branch(
    project_id: uuid.UUID,
    payload: BranchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fork a project into a new branch for exploring alternative directions."""
    # Verify ownership
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    parent = result.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Project not found")

    # Gather full parent state for deep copy
    parent_state = await _gather_project_state(parent, db)

    # Create the branch as a new project, copying parent metadata
    branch_project = Project(
        name=f"{parent.name} — {payload.branch_name}",
        description=parent.description,
        user_id=current_user.id,
        platform=parent.platform,
        audience=parent.audience,
        complexity=parent.complexity,
        tone=parent.tone,
        accent_color=parent.accent_color,
        pathway_id=parent.pathway_id,
        ai_partner_style=parent.ai_partner_style,
        primary_category=getattr(parent, "primary_category", None),
        secondary_category=getattr(parent, "secondary_category", None),
    )
    db.add(branch_project)
    await db.flush()

    # Deep copy all child records from parent state
    await _copy_child_records(parent_state, branch_project.id, current_user.id, db)

    # Record the branch relationship
    branch = ConceptBranch(
        parent_project_id=project_id,
        branch_project_id=branch_project.id,
        branch_name=payload.branch_name,
        description=payload.description,
        created_by=current_user.id,
    )
    db.add(branch)
    await db.flush()

    return {
        "id": str(branch.id),
        "parent_project_id": str(project_id),
        "branch_project_id": str(branch_project.id),
        "branch_name": branch.branch_name,
        "description": branch.description,
        "created_at": branch.created_at.isoformat(),
    }


@router.get("/{project_id}/branches")
async def list_branches(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all branches for a project."""
    result = await db.execute(
        select(ConceptBranch)
        .where(ConceptBranch.parent_project_id == project_id, ConceptBranch.created_by == current_user.id)
        .order_by(ConceptBranch.created_at.desc())
    )
    branches = result.scalars().all()
    return [
        {
            "id": str(b.id),
            "parent_project_id": str(b.parent_project_id),
            "branch_project_id": str(b.branch_project_id),
            "branch_name": b.branch_name,
            "description": b.description,
            "created_at": b.created_at.isoformat(),
        }
        for b in branches
    ]


@router.get("/{project_id}/compare/{branch_id}")
async def compare_branch(
    project_id: uuid.UUID,
    branch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare parent project state with a branch side-by-side."""
    # Verify ownership of parent
    parent_r = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    parent = parent_r.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent project not found")

    # Verify the branch record belongs to this parent
    branch_r = await db.execute(
        select(ConceptBranch).where(
            ConceptBranch.id == branch_id,
            ConceptBranch.parent_project_id == project_id,
            ConceptBranch.created_by == current_user.id,
        )
    )
    branch = branch_r.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Fetch branch project
    bp_r = await db.execute(select(Project).where(Project.id == branch.branch_project_id))
    branch_project = bp_r.scalar_one_or_none()
    if not branch_project:
        raise HTTPException(status_code=404, detail="Branch project not found")

    parent_state = await _gather_project_state(parent, db)
    branch_state = await _gather_project_state(branch_project, db)

    return {
        "branch_name": branch.branch_name,
        "parent": parent_state,
        "branch": branch_state,
    }


@router.post("/{project_id}/merge/{branch_id}")
async def merge_branch(
    project_id: uuid.UUID,
    branch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Merge branch state back into the parent project (overwrites parent child records)."""
    # Verify ownership of parent
    parent_r = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    parent = parent_r.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent project not found")

    # Verify the branch record
    branch_r = await db.execute(
        select(ConceptBranch).where(
            ConceptBranch.id == branch_id,
            ConceptBranch.parent_project_id == project_id,
            ConceptBranch.created_by == current_user.id,
        )
    )
    branch = branch_r.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Fetch branch project
    bp_r = await db.execute(select(Project).where(Project.id == branch.branch_project_id))
    branch_project = bp_r.scalar_one_or_none()
    if not branch_project:
        raise HTTPException(status_code=404, detail="Branch project not found")

    # Gather branch state
    branch_state = await _gather_project_state(branch_project, db)

    # Clear parent's child records
    from app.models.market_analysis import MarketAnalysis
    for model in (DesignSheet, DiscoverySession, Block, PipelineNode, PromptKit,
                  SprintPlan, ModulePathway, ModuleResponse, MarketAnalysis):
        existing = await db.execute(select(model).where(model.project_id == project_id))
        for obj in existing.scalars().all():
            await db.delete(obj)
    await db.flush()

    # Copy branch child records onto parent
    await _copy_child_records(branch_state, project_id, current_user.id, db)

    return {
        "status": "merged",
        "parent_project_id": str(project_id),
        "branch_name": branch.branch_name,
    }
