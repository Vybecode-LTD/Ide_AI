"""
test_artifact_context.py — Tests for the canonical artifact context service.

Covers:
1. v2 context populates from module_responses (not design_sheets)
2. v1 context populates from design_sheets (backward compat)
3. discovery_summary is non-empty for v2 with responses
4. context_for_ai produces usable text for both flow versions
5. Missing project raises 404
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design_sheet import DesignSheet
from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.models.project import Project
from app.models.user import User
from app.services.artifact_context_service import (
    build_artifact_context,
    context_for_ai,
)


class TestBuildArtifactContext:
    """Verify context assembly for v1 and v2 projects."""

    @pytest_asyncio.fixture
    async def v2_project(self, db_session: AsyncSession, test_user: User):
        """Create a v2 project with pathway and module responses."""
        project = Project(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="Clinic Booking App",
            description="Book appointments for local clinics",
            platform="claude-code",
            audience="businesses",
            complexity="medium",
            tone="technical",
            pathway_id="software_product",
            primary_category="software",
            flow_version="v2",
        )
        db_session.add(project)
        await db_session.flush()

        pathway = ModulePathway(
            project_id=project.id,
            modules=["problem_opportunity_framer", "audience_persona_builder"],
            status="active",
        )
        db_session.add(pathway)

        db_session.add(ModuleResponse(
            project_id=project.id,
            module_id="problem_opportunity_framer",
            responses={
                "problem_statement": "Small clinics lose bookings by phone.",
                "target_users": ["clinic admins", "patients"],
            },
            status="complete",
        ))
        db_session.add(ModuleResponse(
            project_id=project.id,
            module_id="audience_persona_builder",
            responses={
                "audience_description": "Healthcare administrators aged 30-50",
            },
            status="active",
        ))
        await db_session.flush()
        return project

    @pytest_asyncio.fixture
    async def v1_project(self, db_session: AsyncSession, test_user: User):
        """Create a v1 project with a design sheet."""
        project = Project(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="Legacy App",
            description="A legacy project",
            flow_version="v1",
        )
        db_session.add(project)
        await db_session.flush()

        sheet = DesignSheet(
            project_id=project.id,
            problem="Users can't find local services",
            audience="Homeowners aged 25-45",
            mvp="Search + booking + payment",
            platform="bubble",
            tone="casual",
            features=[{"name": "Search", "description": "Find services nearby"}],
            confidence_score=75,
        )
        db_session.add(sheet)
        await db_session.flush()
        return project

    @pytest.mark.asyncio
    async def test_v2_context_uses_module_responses(
        self, db_session: AsyncSession, test_user: User, v2_project: Project,
    ):
        ctx = await build_artifact_context(db_session, v2_project.id, test_user.id)

        assert ctx["flow_version"] == "v2"
        assert len(ctx["modules"]) >= 1
        assert ctx["modules"][0]["module_id"] in ("problem_opportunity_framer", "audience_persona_builder")
        assert ctx["discovery_summary"]  # non-empty
        assert "Small clinics lose bookings" in ctx["discovery_summary"]

    @pytest.mark.asyncio
    async def test_v2_module_responses_populated(
        self, db_session: AsyncSession, test_user: User, v2_project: Project,
    ):
        ctx = await build_artifact_context(db_session, v2_project.id, test_user.id)

        # Find the problem_definition module
        pd_mod = next((m for m in ctx["modules"] if m["module_id"] == "problem_opportunity_framer"), None)
        assert pd_mod is not None
        assert pd_mod["responses"]["problem_statement"] == "Small clinics lose bookings by phone."
        assert pd_mod["responses"]["target_users"] == ["clinic admins", "patients"]
        assert pd_mod["status"] == "complete"

    @pytest.mark.asyncio
    async def test_v2_backfills_problem_from_summary(
        self, db_session: AsyncSession, test_user: User, v2_project: Project,
    ):
        """When no DesignSheet exists, context['problem'] is back-filled from discovery_summary."""
        ctx = await build_artifact_context(db_session, v2_project.id, test_user.id)

        assert ctx["sheet"] is None  # no design sheet for v2
        assert ctx["problem"]  # should be non-empty (back-filled)
        assert "Small clinics" in ctx["problem"]

    @pytest.mark.asyncio
    async def test_v1_context_uses_design_sheet(
        self, db_session: AsyncSession, test_user: User, v1_project: Project,
    ):
        ctx = await build_artifact_context(db_session, v1_project.id, test_user.id)

        assert ctx["flow_version"] == "v1"
        assert ctx["problem"] == "Users can't find local services"
        assert ctx["audience"] == "Homeowners aged 25-45"
        assert ctx["mvp"] == "Search + booking + payment"
        assert ctx["confidence_score"] == 75
        assert ctx["modules"] == []  # v1 has no module responses
        assert ctx["discovery_summary"] == ""

    @pytest.mark.asyncio
    async def test_v1_sheet_fields_in_context(
        self, db_session: AsyncSession, test_user: User, v1_project: Project,
    ):
        ctx = await build_artifact_context(db_session, v1_project.id, test_user.id)

        assert ctx["platform"] == "bubble"
        assert ctx["tone"] == "casual"
        assert len(ctx["features"]) == 1
        assert ctx["features"][0]["name"] == "Search"

    @pytest.mark.asyncio
    async def test_missing_project_raises_404(
        self, db_session: AsyncSession, test_user: User,
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await build_artifact_context(db_session, uuid.uuid4(), test_user.id)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_wrong_user_raises_404(
        self, db_session: AsyncSession, test_user: User, v2_project: Project,
    ):
        """A different user_id should not access another user's project."""
        from fastapi import HTTPException

        other_user_id = uuid.uuid4()
        with pytest.raises(HTTPException) as exc_info:
            await build_artifact_context(db_session, v2_project.id, other_user_id)
        assert exc_info.value.status_code == 404


class TestContextForAI:
    """Verify the flat-text summary for AI prompt injection."""

    def test_v1_text_includes_sheet_fields(self):
        ctx = {
            "flow_version": "v1",
            "project_name": "Test App",
            "project_description": "A test",
            "platform": "bubble",
            "audience": "consumers",
            "tone": "casual",
            "complexity": "simple",
            "problem": "Users struggle to find services",
            "mvp": "Search + booking",
            "features": [{"name": "Search"}],
            "tech_constraints": "No backend",
            "success_metric": "100 users/month",
        }
        text = context_for_ai(ctx)
        assert "Test App" in text
        assert "Users struggle to find services" in text
        assert "Search + booking" in text
        assert "No backend" in text

    def test_v2_text_includes_discovery_summary(self):
        ctx = {
            "flow_version": "v2",
            "project_name": "Clinic App",
            "project_description": "Book appointments",
            "platform": "claude-code",
            "audience": "businesses",
            "tone": "technical",
            "complexity": "medium",
            "discovery_summary": "## Problem Definition\n- Problem: Clinics lose bookings\n- Target users: admins",
        }
        text = context_for_ai(ctx)
        assert "Clinic App" in text
        assert "Clinics lose bookings" in text
        assert "Target users: admins" in text

    def test_empty_context_doesnt_crash(self):
        ctx = {
            "flow_version": "v1",
            "project_name": "",
            "project_description": "",
            "platform": "",
            "audience": "",
            "tone": "",
            "complexity": "",
        }
        text = context_for_ai(ctx)
        assert isinstance(text, str)
