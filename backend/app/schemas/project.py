"""
project.py — Pydantic v2 schemas for Project CRUD operations.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str = Field(max_length=200)
    platform: str = Field(default="custom", max_length=50)
    audience: str = Field(default="consumers", max_length=50)
    complexity: str = Field(default="medium", max_length=50)
    tone: str = Field(default="casual", max_length=50)
    description: Optional[str] = None
    accent_color: Optional[str] = Field(default="#00E5FF", max_length=20)
    pathway_id: str = Field(default="software_product", max_length=50)
    ai_partner_style: str = Field(default="strategist", max_length=30)
    primary_category: Optional[str] = Field(None, max_length=50)
    secondary_category: Optional[str] = Field(None, max_length=50)


class ProjectRead(BaseModel):
    """Schema for project response."""
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    platform: str
    audience: str
    complexity: str
    tone: str
    accent_color: str
    pathway_id: str = "software_product"
    ai_partner_style: str = "strategist"
    primary_category: Optional[str] = None
    secondary_category: Optional[str] = None
    pathway_locked: bool = False
    flow_version: str = "v2"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectUpdate(BaseModel):
    """Schema for partial project update."""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    platform: Optional[str] = Field(None, max_length=50)
    audience: Optional[str] = Field(None, max_length=50)
    complexity: Optional[str] = Field(None, max_length=50)
    tone: Optional[str] = Field(None, max_length=50)
    accent_color: Optional[str] = Field(None, max_length=20)
    pathway_id: Optional[str] = Field(None, max_length=50)
    ai_partner_style: Optional[str] = Field(None, max_length=30)
    primary_category: Optional[str] = Field(None, max_length=50)
    secondary_category: Optional[str] = Field(None, max_length=50)
