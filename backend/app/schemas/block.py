"""
block.py — Pydantic v2 schemas for feature Block entities.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.limits import BLOCK_DESCRIPTION_MAX_CHARS


class BlockCreate(BaseModel):
    """Schema for creating a new block."""
    name: str = Field(max_length=200)
    description: Optional[str] = Field(None, max_length=BLOCK_DESCRIPTION_MAX_CHARS)
    category: str = Field(default="feature", max_length=100)
    priority: str = Field(default="mvp", pattern="^(mvp|v2)$")
    effort: str = Field(default="M", pattern="^(S|M|L)$")
    is_mvp: bool = True


class BlockRead(BaseModel):
    """Schema for block response."""
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str] = None
    category: str
    priority: str
    effort: str
    order: int
    is_mvp: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlockUpdate(BaseModel):
    """Schema for partial block update."""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=BLOCK_DESCRIPTION_MAX_CHARS)
    category: Optional[str] = Field(None, max_length=100)
    priority: Optional[str] = Field(None, pattern="^(mvp|v2)$")
    effort: Optional[str] = Field(None, pattern="^(S|M|L)$")
    order: Optional[int] = None
    is_mvp: Optional[bool] = None
