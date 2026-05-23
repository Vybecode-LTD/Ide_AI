"""
admin.py — Admin-only endpoints for user management and audit log access.

All routes here require the calling user to have ``is_admin = True``.
Use the `require_admin` dependency to enforce that gate; it builds on top
of `get_current_user` (Clerk JWT verification) and adds the admin check.

Audit logging is woven into every mutation — see services/audit_service.py.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.admin_audit_log import AdminAuditLog
from app.models.market_analysis import MarketAnalysis
from app.models.project import Project
from app.models.prompt_kit import PromptKit
from app.models.sprint_plan import SprintPlan
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.admin import (
    AdminAdminFlagUpdate,
    AdminAuditLogItem,
    AdminAuditLogResponse,
    AdminOverridesUpdate,
    AdminPlanUpdate,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserListResponse,
)
from app.services.audit_service import log_admin_action
from app.services.entitlement_service import get_limits

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Auth dependency ─────────────────────────────────────────────────


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Reject the request unless the calling user has is_admin = True."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ── User list / detail ──────────────────────────────────────────────


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Match against email, name, display_name"),
    plan: Optional[str] = Query(None, description="Filter by account_type (free/basic/pro)"),
    sort: str = Query("created_at", pattern="^(created_at|updated_at|email|account_type)$"),
    direction: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """Paginated list of users with search + plan filter + sort."""
    base = select(User)

    if search:
        like = f"%{search.lower()}%"
        base = base.where(
            or_(
                sa_func.lower(User.email).like(like),
                sa_func.lower(User.name).like(like),
                sa_func.lower(User.display_name).like(like),
            )
        )

    if plan:
        base = base.where(User.account_type == plan)

    # Total count for pagination
    count_q = select(sa_func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Sort + paginate
    sort_col = getattr(User, sort)
    if direction == "desc":
        sort_col = sort_col.desc()
    rows = await db.execute(
        base.order_by(sort_col).offset((page - 1) * per_page).limit(per_page)
    )
    users = rows.scalars().all()

    # Batch-fetch project counts to avoid N+1
    user_ids = [u.id for u in users]
    project_counts: dict[uuid.UUID, int] = {}
    if user_ids:
        pc = await db.execute(
            select(Project.user_id, sa_func.count(Project.id))
            .where(Project.user_id.in_(user_ids))
            .group_by(Project.user_id)
        )
        project_counts = {uid: count for uid, count in pc.all()}

    items = [
        AdminUserListItem(
            id=u.id,
            email=u.email,
            name=u.name,
            display_name=u.display_name,
            avatar_url=u.avatar_url,
            account_type=u.account_type or "free",
            is_admin=u.is_admin,
            entitlement_overrides=u.entitlement_overrides,
            stripe_customer_id=u.stripe_customer_id,
            project_count=project_counts.get(u.id, 0),
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in users
    ]
    return AdminUserListResponse(items=items, total=total, page=page, per_page=per_page)


async def _get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    """Fetch a user by id or raise 404."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user_detail(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Single-user view with usage counts and effective limits."""
    user = await _get_user_or_404(db, user_id)

    project_count = (
        await db.execute(
            select(sa_func.count(Project.id)).where(Project.user_id == user_id)
        )
    ).scalar() or 0
    market_count = (
        await db.execute(
            select(sa_func.count(MarketAnalysis.id)).where(MarketAnalysis.user_id == user_id)
        )
    ).scalar() or 0
    sprint_count = (
        await db.execute(
            select(sa_func.count(SprintPlan.id)).where(SprintPlan.user_id == user_id)
        )
    ).scalar() or 0
    prompt_count = (
        await db.execute(
            select(sa_func.count(PromptKit.id))
            .join(Project, PromptKit.project_id == Project.id)
            .where(Project.user_id == user_id)
        )
    ).scalar() or 0

    return AdminUserDetail(
        id=user.id,
        email=user.email,
        name=user.name,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        account_type=user.account_type or "free",
        is_admin=user.is_admin,
        entitlement_overrides=user.entitlement_overrides,
        stripe_customer_id=user.stripe_customer_id,
        project_count=project_count,
        created_at=user.created_at,
        updated_at=user.updated_at,
        bio=user.bio,
        inbox_email=user.inbox_email,
        email_verified=user.email_verified,
        oauth_provider=user.oauth_provider,
        clerk_user_id=user.clerk_user_id,
        market_analysis_count=market_count,
        sprint_plan_count=sprint_count,
        prompt_kit_count=prompt_count,
        effective_limits=get_limits(user),
    )


# ── User mutations ──────────────────────────────────────────────────


@router.patch("/users/{user_id}/plan", response_model=AdminUserDetail)
async def update_user_plan(
    user_id: uuid.UUID,
    payload: AdminPlanUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Set a user's account_type directly (bypasses Stripe)."""
    user = await _get_user_or_404(db, user_id)
    before = user.account_type
    if before == payload.account_type:
        # No-op, but still record so admin sees their click registered
        await log_admin_action(
            db, admin.id, "plan_unchanged",
            target_user_id=user.id,
            details={"plan": before},
        )
    else:
        user.account_type = payload.account_type
        await db.flush()
        await log_admin_action(
            db, admin.id, "plan_changed",
            target_user_id=user.id,
            details={"from": before, "to": payload.account_type},
        )

    return await get_user_detail(user_id=user.id, admin=admin, db=db)


@router.patch("/users/{user_id}/overrides", response_model=AdminUserDetail)
async def update_user_overrides(
    user_id: uuid.UUID,
    payload: AdminOverridesUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Set or clear per-user entitlement overrides.

    Pass ``entitlement_overrides: null`` to clear all overrides for this user
    (they'll fall back to plan defaults).
    """
    user = await _get_user_or_404(db, user_id)
    before = user.entitlement_overrides
    user.entitlement_overrides = payload.entitlement_overrides
    await db.flush()
    await log_admin_action(
        db, admin.id, "overrides_updated",
        target_user_id=user.id,
        details={"before": before, "after": payload.entitlement_overrides},
    )
    return await get_user_detail(user_id=user.id, admin=admin, db=db)


@router.patch("/users/{user_id}/admin", response_model=AdminUserDetail)
async def update_user_admin_flag(
    user_id: uuid.UUID,
    payload: AdminAdminFlagUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Grant or revoke admin status.

    Self-revoke is blocked — to step down, ask another admin or update the DB
    directly. Without this guard you could lock yourself out.
    """
    if user_id == admin.id and not payload.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot revoke your own admin status",
        )
    user = await _get_user_or_404(db, user_id)
    before = user.is_admin
    if before != payload.is_admin:
        user.is_admin = payload.is_admin
        await db.flush()
        await log_admin_action(
            db, admin.id,
            "admin_granted" if payload.is_admin else "admin_revoked",
            target_user_id=user.id,
            details={"from": before, "to": payload.is_admin},
        )
    return await get_user_detail(user_id=user.id, admin=admin, db=db)


# ── Audit log ───────────────────────────────────────────────────────


@router.get("/audit-log", response_model=AdminAuditLogResponse)
async def list_audit_log(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    target_user_id: Optional[uuid.UUID] = Query(None),
    action: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """Paginated admin action log, newest first. Optional filters by user / action."""
    base = select(AdminAuditLog)
    if target_user_id:
        base = base.where(AdminAuditLog.target_user_id == target_user_id)
    if action:
        base = base.where(AdminAuditLog.action == action)

    total = (await db.execute(select(sa_func.count()).select_from(base.subquery()))).scalar() or 0

    rows = await db.execute(
        base.order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = rows.scalars().all()

    # Resolve admin + target emails (small batch — page is at most 200 rows)
    user_ids: set[uuid.UUID] = set()
    for e in entries:
        if e.admin_user_id:
            user_ids.add(e.admin_user_id)
        if e.target_user_id:
            user_ids.add(e.target_user_id)
    emails: dict[uuid.UUID, str] = {}
    if user_ids:
        u = await db.execute(select(User.id, User.email).where(User.id.in_(user_ids)))
        emails = {uid: email for uid, email in u.all()}

    items = [
        AdminAuditLogItem(
            id=e.id,
            admin_user_id=e.admin_user_id,
            admin_email=emails.get(e.admin_user_id) if e.admin_user_id else None,
            action=e.action,
            target_user_id=e.target_user_id,
            target_email=emails.get(e.target_user_id) if e.target_user_id else None,
            details=e.details,
            created_at=e.created_at,
        )
        for e in entries
    ]
    return AdminAuditLogResponse(items=items, total=total, page=page, per_page=per_page)
