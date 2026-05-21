"""
sprints.py — Sprint planning endpoints.
Handles AI-powered sprint plan generation, retrieval, updates, and CSV export.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.routers.auth import get_current_user
from app.services import sprint_service
from app.services.entitlement_service import require_feature_usage

router = APIRouter(prefix="/sprints", tags=["sprints"])


async def _verify_project_owner(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Project:
    """Verify the user owns the project. Raises 404 if not found or not owned."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/{project_id}/generate")
async def generate_sprint_plan(
    project_id: uuid.UUID,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a sprint plan from project blocks. Returns SSE stream."""
    await require_feature_usage(current_user, db, "sprint_plans")

    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    async def event_stream():
        async for event in sprint_service.generate_sprint_plan(
            db, project_id, current_user.id, force_regenerate=force
        ):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{project_id}")
async def get_sprint_plan(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the stored sprint plan for a project."""
    await _verify_project_owner(db, project_id, current_user.id)
    plan = await sprint_service.get_sprint_plan(db, project_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No sprint plan found. Generate one first.")
    return {
        "id": str(plan.id),
        "project_id": str(plan.project_id),
        "milestones": plan.milestones,
        "sprints": plan.sprints,
        "timeline": plan.timeline,
        "status": plan.status,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


@router.patch("/{project_id}")
async def update_sprint_plan(
    project_id: uuid.UUID,
    updates: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update sprint plan (manual edits to tasks, assignments, etc.)."""
    await _verify_project_owner(db, project_id, current_user.id)
    plan = await sprint_service.get_sprint_plan(db, project_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No sprint plan found")

    allowed_fields = {"milestones", "sprints", "timeline"}
    for key, value in updates.items():
        if key in allowed_fields:
            setattr(plan, key, value)

    await db.flush()
    return {"detail": "Plan updated"}


@router.get("/{project_id}/export")
async def export_sprint_csv(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export sprint plan as Linear-compatible CSV."""
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    plan = await sprint_service.get_sprint_plan(db, project_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No sprint plan found")

    csv_content = sprint_service.export_as_csv(plan, project.name)

    slug = project.name.lower().replace(" ", "-")[:30]
    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{slug}-sprint-plan.csv"'},
    )


@router.delete("/{project_id}")
async def delete_sprint_plan(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete the sprint plan for a project."""
    await _verify_project_owner(db, project_id, current_user.id)
    plan = await sprint_service.get_sprint_plan(db, project_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No sprint plan found")
    await db.delete(plan)
    return {"detail": "Sprint plan deleted"}
