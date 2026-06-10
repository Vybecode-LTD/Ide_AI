"""
pathways.py — API endpoints for concept pathway definitions.
Serves pathway metadata to the frontend for dynamic UI rendering.
Includes AI-powered pathway detection from project descriptions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.pathways import PathwayRegistry
from app.routers.auth import get_current_user
from app.services.pathway_service import detect_pathway

router = APIRouter(prefix="/pathways", tags=["pathways"])


class DetectRequest(BaseModel):
    # Length-capped: this text is forwarded into an Anthropic call.
    description: str = Field(min_length=1, max_length=5000)


@router.get("")
@router.get("/")
async def list_pathways():
    """Return all available pathway definitions."""
    return [p.to_api_dict() for p in PathwayRegistry.all()]


@router.post("/detect")
@limiter.limit("10/minute")  # authenticated, but each call costs an Anthropic request
async def detect_pathway_endpoint(
    request: Request,
    payload: DetectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-detect the best pathway for a project description (requires auth)."""
    result = await detect_pathway(payload.description)
    # Include full pathway definition alongside the detection result
    try:
        pw = PathwayRegistry.get(result["pathway_id"])
        result["pathway"] = pw.to_api_dict()
    except ValueError:
        pass
    return result


@router.get("/{pathway_id}")
async def get_pathway(pathway_id: str):
    """Return a single pathway definition."""
    try:
        pathway = PathwayRegistry.get(pathway_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Pathway '{pathway_id}' not found")
    return pathway.to_api_dict()
