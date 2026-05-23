"""
admin.py — Pydantic schemas for the /admin API surface.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── User schemas ────────────────────────────────────────────────────


class AdminUserListItem(BaseModel):
    """Row in the paginated admin user list."""

    id: uuid.UUID
    email: str
    name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    account_type: str = "free"
    is_admin: bool = False
    entitlement_overrides: Optional[dict] = None
    stripe_customer_id: Optional[str] = None
    project_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserDetail(AdminUserListItem):
    """Single-user detail view — adds extended fields and usage counts."""

    bio: Optional[str] = None
    inbox_email: Optional[str] = None
    email_verified: bool = False
    oauth_provider: Optional[str] = None
    clerk_user_id: Optional[str] = None
    market_analysis_count: int = 0
    sprint_plan_count: int = 0
    prompt_kit_count: int = 0
    effective_limits: dict


class AdminUserListResponse(BaseModel):
    """Envelope for paginated user list."""

    items: list[AdminUserListItem]
    total: int
    page: int
    per_page: int


# ── Mutation schemas ────────────────────────────────────────────────


class AdminPlanUpdate(BaseModel):
    """Body for PATCH /admin/users/{id}/plan."""

    account_type: str = Field(pattern="^(free|basic|pro)$")


class AdminOverridesUpdate(BaseModel):
    """Body for PATCH /admin/users/{id}/overrides.

    Pass ``null`` (or omit) to clear all overrides for this user.
    Pass a dict to set specific overrides; a value of ``null`` in the dict
    means *unlimited* for that key.
    """

    entitlement_overrides: Optional[dict] = None


class AdminAdminFlagUpdate(BaseModel):
    """Body for PATCH /admin/users/{id}/admin — grant/revoke admin status."""

    is_admin: bool


# ── Audit log schemas ───────────────────────────────────────────────


class AdminAuditLogItem(BaseModel):
    """Row in the paginated audit log list."""

    id: uuid.UUID
    admin_user_id: Optional[uuid.UUID] = None
    admin_email: Optional[str] = None
    action: str
    target_user_id: Optional[uuid.UUID] = None
    target_email: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime


class AdminAuditLogResponse(BaseModel):
    """Envelope for paginated audit log."""

    items: list[AdminAuditLogItem]
    total: int
    page: int
    per_page: int
