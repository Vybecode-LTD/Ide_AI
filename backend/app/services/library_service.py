"""
library_service.py — Business logic for the Library module.
Handles .ideai file export/import and project snapshot management.
"""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
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


IDEAI_FORMAT_VERSION = "1.0"


async def _gather_project_state(project: Project, db: AsyncSession) -> dict:
    """Collect the full state of a project into a serializable dict."""
    project_id = project.id

    # Design sheet
    sheet_r = await db.execute(select(DesignSheet).where(DesignSheet.project_id == project_id))
    sheet = sheet_r.scalar_one_or_none()

    # Discovery sessions
    sess_r = await db.execute(
        select(DiscoverySession)
        .where(DiscoverySession.project_id == project_id)
        .order_by(DiscoverySession.created_at)
    )
    sessions = list(sess_r.scalars().all())

    # Blocks
    blocks_r = await db.execute(
        select(Block).where(Block.project_id == project_id).order_by(Block.order)
    )
    blocks = list(blocks_r.scalars().all())

    # Pipeline nodes
    pipe_r = await db.execute(select(PipelineNode).where(PipelineNode.project_id == project_id))
    pipeline_nodes = list(pipe_r.scalars().all())

    # Market analysis
    market_r = await db.execute(select(MarketAnalysis).where(MarketAnalysis.project_id == project_id))
    market = market_r.scalar_one_or_none()

    # Prompt kits
    pk_r = await db.execute(
        select(PromptKit).where(PromptKit.project_id == project_id).order_by(PromptKit.created_at)
    )
    prompt_kits = list(pk_r.scalars().all())

    # Sprint plan
    sprint_r = await db.execute(select(SprintPlan).where(SprintPlan.project_id == project_id))
    sprint_plan = sprint_r.scalar_one_or_none()

    # Module pathway
    mp_r = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
        .order_by(ModulePathway.updated_at.desc())
    )
    module_pathway = mp_r.scalars().first()

    # Module responses
    mr_r = await db.execute(
        select(ModuleResponse).where(ModuleResponse.project_id == project_id)
    )
    module_responses = list(mr_r.scalars().all())

    # Snapshots (metadata only — not snapshot_data to avoid recursion)
    snap_r = await db.execute(
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_id == project_id)
        .order_by(ProjectSnapshot.version)
    )
    snapshots = list(snap_r.scalars().all())

    state = {
        "project": {
            "name": project.name,
            "description": project.description,
            "platform": project.platform,
            "audience": project.audience,
            "complexity": project.complexity,
            "tone": project.tone,
            "accent_color": project.accent_color,
            "pathway_id": getattr(project, "pathway_id", None),
            "ai_partner_style": getattr(project, "ai_partner_style", None),
            "primary_category": getattr(project, "primary_category", None),
            "secondary_category": getattr(project, "secondary_category", None),
            "created_at": project.created_at.isoformat() if project.created_at else None,
        },
        "design_sheet": None,
        "discovery_sessions": [],
        "blocks": [],
        "pipeline": [],
        "market_analysis": None,
        "prompt_kits": [],
        "sprint_plan": None,
        "module_pathway": None,
        "module_responses": [],
        "snapshots": [],
    }

    if sheet:
        state["design_sheet"] = {
            "problem": sheet.problem,
            "audience": sheet.audience,
            "mvp": sheet.mvp,
            "features": sheet.features,
            "tone": sheet.tone,
            "platform": sheet.platform,
            "tech_constraints": sheet.tech_constraints,
            "success_metric": sheet.success_metric,
            "fields_data": sheet.fields_data,
            "confidence_score": sheet.confidence_score,
        }

    for s in sessions:
        state["discovery_sessions"].append({
            "status": s.status,
            "stage": s.stage,
            "ai_partner_style": getattr(s, "ai_partner_style", "strategist"),
            "messages": s.messages,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    for b in blocks:
        state["blocks"].append({
            "name": b.name,
            "description": b.description,
            "category": b.category,
            "priority": b.priority,
            "effort": b.effort,
            "order": b.order,
            "is_mvp": b.is_mvp,
        })

    for n in pipeline_nodes:
        state["pipeline"].append({
            "layer": n.layer,
            "selected_tool": n.selected_tool,
            "config": n.config,
        })

    if market and market.status == "complete":
        state["market_analysis"] = {
            "target_market": market.target_market,
            "competitive_landscape": market.competitive_landscape,
            "market_metrics": market.market_metrics,
            "revenue_projections": market.revenue_projections,
            "marketing_strategies": market.marketing_strategies,
            "status": market.status,
        }

    for pk in prompt_kits:
        state["prompt_kits"].append({
            "platform": pk.platform,
            "content": pk.content,
            "version": pk.version,
        })

    if sprint_plan and sprint_plan.status == "complete":
        state["sprint_plan"] = {
            "milestones": sprint_plan.milestones,
            "sprints": sprint_plan.sprints,
            "timeline": sprint_plan.timeline,
            "status": sprint_plan.status,
        }

    if module_pathway:
        state["module_pathway"] = {
            "modules": module_pathway.modules,
            "lite_deep_settings": module_pathway.lite_deep_settings,
            "status": module_pathway.status,
        }

    for mr in module_responses:
        state["module_responses"].append({
            "module_id": mr.module_id,
            "responses": mr.responses,
            "status": mr.status,
            "completed_at": mr.completed_at.isoformat() if mr.completed_at else None,
        })

    for snap in snapshots:
        state["snapshots"].append({
            "name": snap.name,
            "description": snap.description,
            "version": snap.version,
            "created_at": snap.created_at.isoformat() if snap.created_at else None,
        })

    return state


async def export_ideai_file(project: Project, db: AsyncSession) -> bytes:
    """Serialize the entire project state into the .ideai JSON format and return as bytes."""
    state = await _gather_project_state(project, db)

    ideai_document = {
        "ideai_version": IDEAI_FORMAT_VERSION,
        "format": "ideai_schema",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        **state,
    }

    return json.dumps(ideai_document, indent=2, ensure_ascii=False, default=str).encode("utf-8")


async def import_ideai_file(data: dict, user_id: uuid.UUID, db: AsyncSession) -> Project:
    """Create a new project from a parsed .ideai file, restoring all associated data."""
    proj_data = data.get("project", {})

    # Create the project
    project = Project(
        user_id=user_id,
        name=proj_data.get("name", "Imported Project"),
        description=proj_data.get("description"),
        platform=proj_data.get("platform", "custom"),
        audience=proj_data.get("audience", "consumers"),
        complexity=proj_data.get("complexity", "medium"),
        tone=proj_data.get("tone", "casual"),
        accent_color=proj_data.get("accent_color", "#00E5FF"),
    )
    db.add(project)
    await db.flush()

    # Restore design sheet
    sheet_data = data.get("design_sheet")
    if sheet_data:
        sheet = DesignSheet(
            project_id=project.id,
            problem=sheet_data.get("problem"),
            audience=sheet_data.get("audience"),
            mvp=sheet_data.get("mvp"),
            features=sheet_data.get("features"),
            tone=sheet_data.get("tone"),
            platform=sheet_data.get("platform"),
            tech_constraints=sheet_data.get("tech_constraints"),
            success_metric=sheet_data.get("success_metric"),
            confidence_score=sheet_data.get("confidence_score", 0),
        )
        db.add(sheet)

    # Restore discovery sessions
    for sess_data in data.get("discovery_sessions", []):
        session = DiscoverySession(
            project_id=project.id,
            status=sess_data.get("status", "completed"),
            stage=sess_data.get("stage", "complete"),
            messages=sess_data.get("messages"),
        )
        db.add(session)

    # Restore blocks
    for block_data in data.get("blocks", []):
        block = Block(
            project_id=project.id,
            name=block_data.get("name", "Untitled Block"),
            description=block_data.get("description"),
            category=block_data.get("category", "feature"),
            priority=block_data.get("priority", "mvp"),
            effort=block_data.get("effort", "M"),
            order=block_data.get("order", 0),
            is_mvp=block_data.get("is_mvp", True),
        )
        db.add(block)

    # Restore pipeline nodes
    for pipe_data in data.get("pipeline", []):
        node = PipelineNode(
            project_id=project.id,
            layer=pipe_data.get("layer", ""),
            selected_tool=pipe_data.get("selected_tool", ""),
            config=pipe_data.get("config"),
        )
        db.add(node)

    # Restore market analysis
    market_data = data.get("market_analysis")
    if market_data:
        market = MarketAnalysis(
            project_id=project.id,
            user_id=user_id,
            target_market=market_data.get("target_market"),
            competitive_landscape=market_data.get("competitive_landscape"),
            market_metrics=market_data.get("market_metrics"),
            revenue_projections=market_data.get("revenue_projections"),
            marketing_strategies=market_data.get("marketing_strategies"),
            status=market_data.get("status", "complete"),
        )
        db.add(market)

    await db.flush()
    return project


async def create_snapshot(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    description: str | None,
    db: AsyncSession,
) -> ProjectSnapshot:
    """Take a named snapshot of the current project state."""
    # Verify project exists and belongs to user
    proj_r = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = proj_r.scalar_one_or_none()
    if not project:
        raise ValueError("Project not found")

    # Determine next version number
    max_version_r = await db.execute(
        select(sa_func.coalesce(sa_func.max(ProjectSnapshot.version), 0))
        .where(ProjectSnapshot.project_id == project_id)
    )
    next_version = max_version_r.scalar() + 1

    # Gather current state
    state = await _gather_project_state(project, db)

    snapshot = ProjectSnapshot(
        project_id=project_id,
        user_id=user_id,
        name=name,
        description=description,
        snapshot_data=state,
        version=next_version,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


async def list_snapshots(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> list[ProjectSnapshot]:
    """List all snapshots for a project owned by the user."""
    # Verify ownership
    proj_r = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    if not proj_r.scalar_one_or_none():
        raise ValueError("Project not found")

    result = await db.execute(
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_id == project_id)
        .order_by(ProjectSnapshot.version.desc())
    )
    return list(result.scalars().all())


async def restore_snapshot(
    snapshot_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Project:
    """Restore a project to a previously saved snapshot state."""
    # Fetch the snapshot
    snap_r = await db.execute(
        select(ProjectSnapshot).where(
            ProjectSnapshot.id == snapshot_id,
            ProjectSnapshot.user_id == user_id,
        )
    )
    snapshot = snap_r.scalar_one_or_none()
    if not snapshot:
        raise ValueError("Snapshot not found")

    project_id = snapshot.project_id
    state = snapshot.snapshot_data

    # Fetch the project
    proj_r = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_r.scalar_one_or_none()
    if not project:
        raise ValueError("Project not found")

    # Update project metadata from snapshot
    proj_state = state.get("project", {})
    project.name = proj_state.get("name", project.name)
    project.description = proj_state.get("description", project.description)
    project.platform = proj_state.get("platform", project.platform)
    project.audience = proj_state.get("audience", project.audience)
    project.complexity = proj_state.get("complexity", project.complexity)
    project.tone = proj_state.get("tone", project.tone)
    project.accent_color = proj_state.get("accent_color", project.accent_color)
    # Restore pathway/category fields if present in snapshot
    if "pathway_id" in proj_state:
        project.pathway_id = proj_state["pathway_id"]
    if "ai_partner_style" in proj_state:
        project.ai_partner_style = proj_state["ai_partner_style"]
    if "primary_category" in proj_state:
        project.primary_category = proj_state["primary_category"]
    if "secondary_category" in proj_state:
        project.secondary_category = proj_state["secondary_category"]

    # Clear existing child data
    for model in (DesignSheet, DiscoverySession, Block, PipelineNode, MarketAnalysis,
                  PromptKit, SprintPlan, ModulePathway, ModuleResponse):
        existing = await db.execute(select(model).where(model.project_id == project_id))
        for obj in existing.scalars().all():
            await db.delete(obj)

    await db.flush()

    # Restore design sheet
    sheet_data = state.get("design_sheet")
    if sheet_data:
        sheet = DesignSheet(
            project_id=project_id,
            problem=sheet_data.get("problem"),
            audience=sheet_data.get("audience"),
            mvp=sheet_data.get("mvp"),
            features=sheet_data.get("features"),
            tone=sheet_data.get("tone"),
            platform=sheet_data.get("platform"),
            tech_constraints=sheet_data.get("tech_constraints"),
            success_metric=sheet_data.get("success_metric"),
            confidence_score=sheet_data.get("confidence_score", 0),
        )
        db.add(sheet)

    # Restore discovery sessions
    for sess_data in state.get("discovery_sessions", []):
        session = DiscoverySession(
            project_id=project_id,
            status=sess_data.get("status", "completed"),
            stage=sess_data.get("stage", "complete"),
            messages=sess_data.get("messages"),
        )
        db.add(session)

    # Restore blocks
    for block_data in state.get("blocks", []):
        block = Block(
            project_id=project_id,
            name=block_data.get("name", "Untitled Block"),
            description=block_data.get("description"),
            category=block_data.get("category", "feature"),
            priority=block_data.get("priority", "mvp"),
            effort=block_data.get("effort", "M"),
            order=block_data.get("order", 0),
            is_mvp=block_data.get("is_mvp", True),
        )
        db.add(block)

    # Restore pipeline nodes
    for pipe_data in state.get("pipeline", []):
        node = PipelineNode(
            project_id=project_id,
            layer=pipe_data.get("layer", ""),
            selected_tool=pipe_data.get("selected_tool", ""),
            config=pipe_data.get("config"),
        )
        db.add(node)

    # Restore market analysis
    market_data = state.get("market_analysis")
    if market_data:
        market = MarketAnalysis(
            project_id=project_id,
            user_id=user_id,
            target_market=market_data.get("target_market"),
            competitive_landscape=market_data.get("competitive_landscape"),
            market_metrics=market_data.get("market_metrics"),
            revenue_projections=market_data.get("revenue_projections"),
            marketing_strategies=market_data.get("marketing_strategies"),
            status=market_data.get("status", "complete"),
        )
        db.add(market)

    # Restore prompt kits
    for pk_data in state.get("prompt_kits", []):
        pk = PromptKit(
            project_id=project_id,
            platform=pk_data.get("platform", "generic"),
            content=pk_data.get("content", ""),
            version=pk_data.get("version", 1),
        )
        db.add(pk)

    # Restore sprint plan
    sprint_data = state.get("sprint_plan")
    if sprint_data:
        sprint = SprintPlan(
            project_id=project_id,
            user_id=user_id,
            milestones=sprint_data.get("milestones"),
            sprints=sprint_data.get("sprints"),
            timeline=sprint_data.get("timeline"),
            status=sprint_data.get("status", "complete"),
        )
        db.add(sprint)

    # Restore module pathway
    mp_data = state.get("module_pathway")
    if mp_data:
        mp = ModulePathway(
            project_id=project_id,
            modules=mp_data.get("modules", []),
            lite_deep_settings=mp_data.get("lite_deep_settings", {}),
            status=mp_data.get("status", "pending"),
        )
        db.add(mp)

    # Restore module responses
    for mr_data in state.get("module_responses", []):
        mr = ModuleResponse(
            project_id=project_id,
            module_id=mr_data.get("module_id", ""),
            responses=mr_data.get("responses", {}),
            status=mr_data.get("status", "pending"),
        )
        db.add(mr)

    await db.flush()
    return project
