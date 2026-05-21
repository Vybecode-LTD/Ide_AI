"""
branching.py — Concept branching (git-like fork for ideas).
Creates a copy of a project so users can explore alternative directions.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.models.block import Block
from app.models.concept_branch import ConceptBranch
from app.models.design_sheet import DesignSheet
from app.models.market_analysis import MarketAnalysis
from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.models.pipeline_node import PipelineNode
from app.models.project import Project
from app.models.project_snapshot import ProjectSnapshot
from app.models.prompt_kit import PromptKit
from app.models.session import DiscoverySession
from app.models.sprint_plan import SprintPlan
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.entitlement_service import require_project_slot
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


class MergeRequest(BaseModel):
    """Optional body for selective merge. Omit or pass empty sections to merge everything."""
    sections: Optional[list[str]] = Field(
        default=None,
        description=(
            "Sections to merge from the branch. "
            "Valid: design_sheet, discovery_sessions, blocks, pipeline, "
            "prompt_kits, sprint_plan, module_pathway, module_responses, market_analysis. "
            "Omit or null to merge all sections (full overwrite)."
        ),
    )


# All section keys that _copy_child_records supports.
_ALL_SECTIONS = frozenset({
    "design_sheet",
    "discovery_sessions",
    "blocks",
    "pipeline",
    "prompt_kits",
    "sprint_plan",
    "module_pathway",
    "module_responses",
    "market_analysis",
})

# Maps section key → ORM model(s) to delete during selective merge.
_SECTION_MODELS: dict[str, list[type]] = {
    "design_sheet": [DesignSheet],
    "discovery_sessions": [DiscoverySession],
    "blocks": [Block],
    "pipeline": [PipelineNode],
    "prompt_kits": [PromptKit],
    "sprint_plan": [SprintPlan],
    "module_pathway": [ModulePathway],
    "module_responses": [ModuleResponse],
    "market_analysis": [MarketAnalysis],
}


def _compute_diff(parent: dict, branch: dict) -> dict[str, dict]:
    """Compare two project states section-by-section and return diff metadata.

    Returns a dict keyed by section name with:
      - changed: bool — whether the section differs between parent and branch
      - parent_summary: str — short description of parent state
      - branch_summary: str — short description of branch state
    """
    diffs: dict[str, dict] = {}
    for key in _ALL_SECTIONS:
        p_val = parent.get(key)
        b_val = branch.get(key)

        # Normalize: treat None and [] / {} the same as "empty"
        p_empty = p_val is None or p_val == [] or p_val == {}
        b_empty = b_val is None or b_val == [] or b_val == {}

        changed = (p_val != b_val)

        diffs[key] = {
            "changed": changed,
            "parent_summary": _summarize(key, p_val, p_empty),
            "branch_summary": _summarize(key, b_val, b_empty),
        }
    return diffs


def _summarize(section: str, val: object, empty: bool) -> str:
    """Generate a one-line summary for a section's state."""
    if empty:
        return "empty"
    if isinstance(val, list):
        return f"{len(val)} item{'s' if len(val) != 1 else ''}"
    if isinstance(val, dict):
        status = val.get("status")
        if status:
            return f"present ({status})"
        return "present"
    return "present"


async def _copy_child_records(
    state: dict,
    target_project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    sections: frozenset[str] | None = None,
) -> None:
    """Deep-copy child records from a gathered project state onto a target project.

    Args:
        sections: If provided, only copy these sections. None = copy everything.
    """
    include = sections or _ALL_SECTIONS

    # Design sheet
    if "design_sheet" in include:
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
                fields_data=sheet_data.get("fields_data"),
                confidence_score=sheet_data.get("confidence_score", 0),
            ))

    # Discovery sessions
    if "discovery_sessions" in include:
        for s in state.get("discovery_sessions", []):
            db.add(DiscoverySession(
                project_id=target_project_id,
                status=s.get("status", "completed"),
                stage=s.get("stage", "complete"),
                ai_partner_style=s.get("ai_partner_style", "strategist"),
                messages=s.get("messages"),
            ))

    # Blocks
    if "blocks" in include:
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
    if "pipeline" in include:
        for n in state.get("pipeline", []):
            db.add(PipelineNode(
                project_id=target_project_id,
                layer=n.get("layer", ""),
                selected_tool=n.get("selected_tool", ""),
                config=n.get("config"),
            ))

    # Prompt kits
    if "prompt_kits" in include:
        for pk in state.get("prompt_kits", []):
            db.add(PromptKit(
                project_id=target_project_id,
                platform=pk.get("platform", "generic"),
                content=pk.get("content", ""),
                version=pk.get("version", 1),
            ))

    # Sprint plan
    if "sprint_plan" in include:
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
    if "module_pathway" in include:
        mp_data = state.get("module_pathway")
        if mp_data:
            db.add(ModulePathway(
                project_id=target_project_id,
                modules=mp_data.get("modules", []),
                lite_deep_settings=mp_data.get("lite_deep_settings", {}),
                status=mp_data.get("status", "pending"),
            ))

    # Module responses
    if "module_responses" in include:
        for mr in state.get("module_responses", []):
            completed_raw = mr.get("completed_at")
            completed_at = None
            if completed_raw:
                try:
                    completed_at = datetime.fromisoformat(completed_raw)
                except (ValueError, TypeError):
                    pass
            db.add(ModuleResponse(
                project_id=target_project_id,
                module_id=mr.get("module_id", ""),
                responses=mr.get("responses", {}),
                status=mr.get("status", "pending"),
                completed_at=completed_at,
            ))

    # Market analysis
    if "market_analysis" in include:
        market_data = state.get("market_analysis")
        if market_data:
            db.add(MarketAnalysis(
                project_id=target_project_id,
                user_id=user_id,
                target_market=market_data.get("target_market"),
                competitive_landscape=market_data.get("competitive_landscape"),
                market_metrics=market_data.get("market_metrics"),
                revenue_projections=market_data.get("revenue_projections"),
                marketing_strategies=market_data.get("marketing_strategies"),
                status=market_data.get("status", "complete"),
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

    await require_project_slot(current_user, db)

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
        "diff": _compute_diff(parent_state, branch_state),
    }


@router.post("/{project_id}/merge/{branch_id}")
async def merge_branch(
    project_id: uuid.UUID,
    branch_id: uuid.UUID,
    payload: Optional[MergeRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Merge branch state back into the parent project.

    By default, overwrites all parent child records (full merge).
    Pass ``sections`` in the body to selectively merge only specific sections
    (e.g. ``["blocks", "pipeline"]``). Un-listed sections are left unchanged.

    A pre-merge snapshot of the parent is created automatically so the user
    can roll back via the Library snapshot restore endpoint.
    """
    # Validate sections early
    merge_sections: frozenset[str] | None = None
    if payload and payload.sections is not None:
        invalid = set(payload.sections) - _ALL_SECTIONS
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid sections: {', '.join(sorted(invalid))}. "
                       f"Valid: {', '.join(sorted(_ALL_SECTIONS))}",
            )
        merge_sections = frozenset(payload.sections)

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

    # ── Pre-merge snapshot ───────────────────────────────────────────
    parent_state = await _gather_project_state(parent, db)

    # Determine next version number
    from sqlalchemy import func as sa_func
    max_ver_r = await db.execute(
        select(sa_func.coalesce(sa_func.max(ProjectSnapshot.version), 0))
        .where(ProjectSnapshot.project_id == project_id)
    )
    next_version = (max_ver_r.scalar() or 0) + 1

    section_label = (
        f" ({', '.join(sorted(merge_sections))})" if merge_sections else ""
    )
    db.add(ProjectSnapshot(
        project_id=project_id,
        user_id=current_user.id,
        name=f"Pre-merge: {branch.branch_name}{section_label}",
        description="Automatic snapshot created before branch merge.",
        snapshot_data=parent_state,
        version=next_version,
    ))
    await db.flush()

    # ── Gather branch state ──────────────────────────────────────────
    branch_state = await _gather_project_state(branch_project, db)

    # ── Delete + copy ────────────────────────────────────────────────
    sections_to_clear = merge_sections or _ALL_SECTIONS
    for section_key in sections_to_clear:
        for model in _SECTION_MODELS.get(section_key, []):
            existing = await db.execute(
                select(model).where(model.project_id == project_id)
            )
            for obj in existing.scalars().all():
                await db.delete(obj)
    await db.flush()

    await _copy_child_records(
        branch_state, project_id, current_user.id, db,
        sections=merge_sections,
    )

    return {
        "status": "merged",
        "parent_project_id": str(project_id),
        "branch_name": branch.branch_name,
        "sections_merged": sorted(sections_to_clear),
        "pre_merge_snapshot_version": next_version,
    }
