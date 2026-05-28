"""
pipeline.py — Pipeline builder router. Tech stack recommendations and management.
"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.design_sheet import DesignSheet
from app.models.pipeline_node import PipelineNode
from app.models.project import Project
from app.models.user import User
from app.pathways import PathwayRegistry
from app.routers.auth import get_current_user
from app.schemas.pipeline import PipelineNodeRead, PipelineNodeUpdate
from app.services.artifact_context_service import build_artifact_context
from app.services.pipeline_service import (
    check_compatibility,
    estimate_cost,
    recommend_pipeline,
)

router = APIRouter(prefix="/projects/{project_id}/pipeline", tags=["pipeline"])


@router.get("", response_model=dict)
async def get_pipeline(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the pipeline configuration for a project."""
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    pw = PathwayRegistry.get_or_default(project.pathway_id)

    result = await db.execute(
        select(PipelineNode).where(PipelineNode.project_id == project_id)
    )
    nodes = list(result.scalars().all())

    return {
        "nodes": [PipelineNodeRead.model_validate(n).model_dump() for n in nodes],
        "cost_estimate": estimate_cost(nodes, pathway=pw),
        "warnings": check_compatibility(nodes),
        "available_layers": {
            layer: info["tools"] for layer, info in pw.domain_layers.items()
        },
    }


@router.post("/recommend", response_model=dict)
async def ai_recommend_pipeline(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-recommend a pipeline based on the design sheet (v1) or module responses (v2)."""
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    pw = PathwayRegistry.get_or_default(project.pathway_id)

    if getattr(project, "flow_version", "v1") == "v2":
        # v2: use unified artifact context from module responses
        artifact_ctx = await build_artifact_context(db, project_id, current_user.id)
        nodes, reasoning, cost_est = await recommend_pipeline(
            db, project_id=project_id, complexity=project.complexity,
            pathway=pw, artifact_ctx=artifact_ctx,
        )
    else:
        # v1: require design sheet
        sheet_result = await db.execute(
            select(DesignSheet).where(DesignSheet.project_id == project_id)
        )
        sheet = sheet_result.scalar_one_or_none()
        if not sheet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design sheet not found")
        nodes, reasoning, cost_est = await recommend_pipeline(
            db, sheet, project_id, project.complexity, pathway=pw,
        )

    return {
        "nodes": [PipelineNodeRead.model_validate(n).model_dump() for n in nodes],
        "reasoning": reasoning,
        "cost_estimate": cost_est,
        "warnings": check_compatibility(nodes),
        "available_layers": {
            layer: info["tools"] for layer, info in pw.domain_layers.items()
        },
    }


@router.patch("/{layer}", response_model=PipelineNodeRead)
async def update_pipeline_layer(
    project_id: uuid.UUID,
    layer: str,
    payload: PipelineNodeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a specific pipeline layer's tool selection."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(PipelineNode).where(
            PipelineNode.project_id == project_id, PipelineNode.layer == layer
        )
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline layer not found")

    if payload.selected_tool:
        node.selected_tool = payload.selected_tool
    if payload.config is not None:
        node.config = payload.config

    await db.flush()
    return node


@router.post("/ui-skeleton", response_model=dict)
async def generate_ui_skeleton(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a UI skeleton screen list from the design sheet."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    sheet_result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    sheet = sheet_result.scalar_one_or_none()
    if not sheet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design sheet not found")

    from app.services.ai_service import client as ai_client
    response = await ai_client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=2048,
        system="You are a UI/UX designer. Return only valid JSON.",
        messages=[{
            "role": "user",
            "content": f"""Generate a list of screens/pages for this app:
Problem: {sheet.problem}
Audience: {sheet.audience}
Features: {json.dumps(sheet.features or [])}
MVP: {sheet.mvp}

Return JSON: [{{"name": "Screen Name", "description": "What it does", "components": ["component1", "component2"]}}]"""
        }],
    )

    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        screens = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        screens = []

    return {"screens": screens}
