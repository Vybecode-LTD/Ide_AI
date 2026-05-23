"""
entitlement_service.py — Plan-based feature gates.
Checks whether a user's current plan allows a specific action.
"""
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_analysis import MarketAnalysis
from app.models.project import Project
from app.models.prompt_kit import PromptKit
from app.models.sprint_plan import SprintPlan
from app.models.user import User


# ── Plan limits ──────────────────────────────────────────────────
# None means unlimited.
PLAN_LIMITS: dict[str, dict[str, int | None]] = {
    "free": {
        "projects": 3,
        "prompt_packages": 0,
        "market_analysis": 0,
        "sprint_plans": 0,
    },
    "basic": {
        "projects": 25,
        "prompt_packages": 10,
        "market_analysis": 5,
        "sprint_plans": 10,
    },
    "pro": {
        "projects": None,
        "prompt_packages": None,
        "market_analysis": None,
        "sprint_plans": None,
    },
}


def get_limits(user: User) -> dict[str, int | None]:
    """Return the effective limits for a user.

    Plan defaults are looked up by ``account_type``, then merged with any
    per-user ``entitlement_overrides`` (which admins set via /admin/users/{id}/overrides).
    Override semantics: any key present in overrides wins. A value of ``None``
    in overrides means *unlimited* for that key.
    """
    plan = getattr(user, "account_type", "free") or "free"
    base = dict(PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]))
    overrides = getattr(user, "entitlement_overrides", None) or {}
    for key, value in overrides.items():
        if key in base:
            base[key] = value
    return base


async def check_project_limit(user: User, db: AsyncSession) -> dict[str, Any]:
    """Check whether the user can create another project.

    Returns {"allowed": True/False, "current": int, "limit": int|None, "plan": str}.
    """
    limits = get_limits(user)
    max_projects = limits["projects"]
    if max_projects is None:
        return {"allowed": True, "current": 0, "limit": None, "plan": user.account_type or "free"}

    result = await db.execute(
        select(sa_func.count(Project.id)).where(Project.user_id == user.id)
    )
    current = result.scalar() or 0
    return {
        "allowed": current < max_projects,
        "current": current,
        "limit": max_projects,
        "plan": user.account_type or "free",
    }


def check_feature(user: User, feature: str) -> dict[str, Any]:
    """Check whether the user's plan allows a feature (by limit key).

    For non-countable gates (like prompt_packages), returns whether the limit > 0.
    """
    limits = get_limits(user)
    limit = limits.get(feature)
    allowed = limit is None or limit > 0
    return {
        "allowed": allowed,
        "limit": limit,
        "plan": user.account_type or "free",
    }


# ── Reusable guards ─────────────────────────────────────────────────


async def require_project_slot(user: User, db: AsyncSession) -> None:
    """Raise 403 if the user has reached their project limit.

    Call this before **every** project-creation code path (blank project,
    template use, inbox promote, branch, .ideai import).
    """
    check = await check_project_limit(user, db)
    if not check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "project_limit_reached",
                "current": check["current"],
                "limit": check["limit"],
                "plan": check["plan"],
                "message": "Project limit reached. Upgrade your plan to create more projects.",
            },
        )


async def check_feature_usage(
    user: User,
    db: AsyncSession,
    feature: str,
) -> dict[str, Any]:
    """Count-aware feature check.

    Returns ``{"allowed": bool, "current": int, "limit": int | None, "plan": str}``.
    """
    limits = get_limits(user)
    limit = limits.get(feature)
    plan = user.account_type or "free"

    if limit is None:
        return {"allowed": True, "current": 0, "limit": None, "plan": plan}

    user_id = user.id

    if feature == "prompt_packages":
        r = await db.execute(
            select(sa_func.count(PromptKit.id))
            .join(Project, PromptKit.project_id == Project.id)
            .where(Project.user_id == user_id)
        )
        current = r.scalar() or 0
    elif feature == "market_analysis":
        r = await db.execute(
            select(sa_func.count(MarketAnalysis.id))
            .where(
                MarketAnalysis.user_id == user_id,
                MarketAnalysis.status.in_(["complete", "generating"]),
            )
        )
        current = r.scalar() or 0
    elif feature == "sprint_plans":
        r = await db.execute(
            select(sa_func.count(SprintPlan.id))
            .where(
                SprintPlan.user_id == user_id,
                SprintPlan.status.in_(["complete", "generating"]),
            )
        )
        current = r.scalar() or 0
    else:
        current = 0

    return {"allowed": current < limit, "current": current, "limit": limit, "plan": plan}


async def require_feature_usage(
    user: User,
    db: AsyncSession,
    feature: str,
) -> None:
    """Raise 403 if the user has exhausted their count-limited feature allowance."""
    check = await check_feature_usage(user, db, feature)
    if not check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "feature_limit_reached",
                "feature": feature,
                "current": check["current"],
                "limit": check["limit"],
                "plan": check["plan"],
                "message": f"{feature.replace('_', ' ').title()} limit reached. Upgrade your plan.",
            },
        )
