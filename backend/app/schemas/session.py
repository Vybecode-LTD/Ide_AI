"""
session.py — Pydantic v2 schemas for Discovery Session and message payloads.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class SessionCreate(BaseModel):
    """Schema for starting or resuming a discovery session."""
    project_id: uuid.UUID
    force_new: bool = False
    scope_module_ids: list[str] | None = None

    @field_validator("scope_module_ids", mode="before")
    @classmethod
    def normalize_empty_scope(cls, v: list[str] | None) -> list[str] | None:
        if isinstance(v, list) and len(v) == 0:
            return None
        return v


class SessionRead(BaseModel):
    """Schema for session response."""
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    stage: str
    ai_partner_style: str = "strategist"
    messages: list = []
    scope_module_ids: list[str] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessagePayload(BaseModel):
    """Schema for sending a message in a discovery session."""
    content: str


class ProgressPayload(BaseModel):
    """Schema for saving discovery session progress (auto-save).

    The client sends only stage and a message count — never a full messages
    array — so a stale browser tab cannot overwrite canonical server-side
    messages.
    """
    stage: str | None = None
    client_message_count: int | None = None


class PartnerUpdatePayload(BaseModel):
    """Schema for switching AI partner mid-session."""
    ai_partner_style: str
