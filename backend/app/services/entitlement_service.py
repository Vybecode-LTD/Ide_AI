"""
entitlement_service.py — Plan-based feature gates.
Checks whether a user's current plan allows a specific action.
"""
import uuid
from typing import Any

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
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
    """Return the plan limits for a user based on their account_type."""
    plan = getattr(user, "account_type", "free") or "free"
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


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
