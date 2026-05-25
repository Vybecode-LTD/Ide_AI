"""
market.py — Market Analysis router. Handles generation, retrieval, report export, and file exports.
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
from app.schemas.market_analysis import MarketAnalysisGenerate, MarketAnalysisRead
from app.services import market_service
from app.services import market_export_service
from app.services.entitlement_service import require_feature_usage
from app.services.export_service import safe_filename_slug

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/{project_id}/generate")
async def generate_analysis(
    project_id: uuid.UUID,
    payload: MarketAnalysisGenerate = MarketAnalysisGenerate(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger market analysis generation. Returns SSE stream with progress events."""
    await require_feature_usage(current_user, db, "market_analysis")

    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    async def event_stream():
        async for event in market_service.generate_market_analysis(
            db, project_id, current_user.id, payload.force_regenerate
        ):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{project_id}", response_model=MarketAnalysisRead)
async def get_analysis(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the stored market analysis for a project."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    analysis = await market_service.get_analysis(db, project_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No market analysis found. Generate one first.")

    return analysis


@router.get("/{project_id}/report")
async def get_report(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a formatted market analysis report."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    report = await market_service.generate_report(db, project_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No complete market analysis found. Generate one first.",
        )

    return report


MARKET_EXPORT_CONTENT_TYPES = {
    "pdf": ("application/pdf", "market-analysis.pdf"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "market-analysis.docx"),
    "txt": ("text/plain", "market-analysis.txt"),
}


@router.get("/{project_id}/export")
async def export_market_analysis(
    project_id: uuid.UUID,
    format: str = "pdf",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export market analysis as PDF, DOCX, or TXT."""
    if format not in MARKET_EXPORT_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Supported: pdf, docx, txt")

    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    analysis = await market_service.get_analysis(db, project_id)
    if not analysis or analysis.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No complete market analysis found. Generate one first.",
        )

    content_type, filename = MARKET_EXPORT_CONTENT_TYPES[format]

    generators = {
        "pdf": market_export_service.generate_pdf,
        "docx": market_export_service.generate_docx,
        "txt": market_export_service.generate_text,
    }

    try:
        content = generators[format](analysis, project.name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Market analysis export failed ({format}): {str(e)}",
        )

    if isinstance(content, str):
        content = content.encode("utf-8")

    slug = safe_filename_slug(project.name or "", fallback="project")
    ext_filename = f"{slug}-{filename}"

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{ext_filename}"'},
    )
