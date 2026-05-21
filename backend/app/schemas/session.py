"""
session.py — Pydantic v2 schemas for Discovery Session and message payloads.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    """Schema for starting or resuming a discovery session."""
    project_id: uuid.UUID
    force_new: bool = False


class SessionRead(BaseModel):
    """Schema for session response."""
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    stage: str
    ai_partner_style: str = "strategist"
    messages: list = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessagePayload(BaseModel):
    """Schema for sending a message in a discovery session."""
    content: str


class ProgressPayload(BaseModel):
    """Schema for saving discovery session progress (auto-save)."""
    messages: list = []
    stage: str


class PartnerUpdatePayload(BaseModel):
    """Schema for switching AI partner mid-session."""
    ai_partner_style: str
