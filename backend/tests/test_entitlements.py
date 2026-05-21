"""
test_entitlements.py — Tests for centralized entitlement guards.

Covers:
    1. Plan limit definitions
    2. Project slot guard (free / basic / pro)
    3. Feature usage counting
"""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.user import User
from app.services.entitlement_service import (
    PLAN_LIMITS,
    check_project_limit,
    get_limits,
    require_project_slot,
)


class TestPlanLimits:
    def test_free_plan_has_3_projects(self):
        assert PLAN_LIMITS["free"]["projects"] == 3

    def test_basic_plan_has_25_projects(self):
        assert PLAN_LIMITS["basic"]["projects"] == 25

    def test_pro_plan_is_unlimited(self):
        assert PLAN_LIMITS["pro"]["projects"] is None

    def test_free_plan_blocks_features(self):
        assert PLAN_LIMITS["free"]["prompt_packages"] == 0
        assert PLAN_LIMITS["free"]["market_analysis"] == 0
        assert PLAN_LIMITS["free"]["sprint_plans"] == 0

    def test_get_limits_defaults_to_free(self):
        """Unknown account_type should fall back to free limits."""
        user = User(id=uuid.uuid4(), email="t@x.com", account_type="nonexistent")
        assert get_limits(user) == PLAN_LIMITS["free"]


class TestProjectSlot:
    @pytest.mark.asyncio
    async def test_free_user_can_create_first_project(self, db_session: AsyncSession, test_user: User):
        """Free user with no projects should pass the guard."""
        check = await check_project_limit(test_user, db_session)
        assert check["allowed"] is True
        assert check["current"] == 0
        # Guard should not raise
        await require_project_slot(test_user, db_session)

    @pytest.mark.asyncio
    async def test_free_user_blocked_at_limit(self, db_session: AsyncSession, test_user: User):
        """Free user at 3 projects should be blocked."""
        for i in range(3):
            db_session.add(Project(
                id=uuid.uuid4(),
                user_id=test_user.id,
                name=f"Project {i}",
                description=f"Test project {i}",
            ))
        await db_session.flush()

        check = await check_project_limit(test_user, db_session)
        assert check["allowed"] is False
        assert check["current"] == 3
        assert check["limit"] == 3

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await require_project_slot(test_user, db_session)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "project_limit_reached"

    @pytest.mark.asyncio
    async def test_basic_user_can_exceed_free_limit(self, db_session: AsyncSession, test_user: User):
        """Basic user should be allowed more than 3 projects."""
        test_user.account_type = "basic"
        for i in range(4):
            db_session.add(Project(
                id=uuid.uuid4(),
                user_id=test_user.id,
                name=f"Project {i}",
                description=f"Test project {i}",
            ))
        await db_session.flush()

        check = await check_project_limit(test_user, db_session)
        assert check["allowed"] is True
        assert check["current"] == 4
        # Should not raise
        await require_project_slot(test_user, db_session)

    @pytest.mark.asyncio
    async def test_pro_user_always_allowed(self, db_session: AsyncSession, test_user: User):
        """Pro user should never be blocked."""
        test_user.account_type = "pro"
        check = await check_project_limit(test_user, db_session)
        assert check["allowed"] is True
        assert check["limit"] is None
