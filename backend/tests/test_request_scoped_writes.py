"""
test_request_scoped_writes.py — edits must survive a production-style session.

Regression tests for the "edit fails and rolls back" fault: a column declared
with ``onupdate=func.now()`` is expired by the UPDATE, and serializing the
response then tried to lazy-load it outside the async context. The request
ended in a 500 and ``get_db`` rolled the change back.

These tests use the ``request_client`` fixture (one session per request, as in
production). The shared-session ``client`` fixtures elsewhere cannot see this.
"""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.models.block import Block
from app.models.design_sheet import DesignSheet
from app.models.pipeline_node import PipelineNode
from app.models.project import Project
from app.models.sprint_plan import SprintPlan
from tests.conftest import TestSessionLocal


async def _make_project(db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
    project = Project(id=uuid.uuid4(), user_id=user_id, name="Before", description="d")
    db.add(project)
    await db.flush()
    return project.id


class TestEditsPersist:
    """Each PATCH returns 200 with a timestamp and the change is stored."""

    @pytest.mark.asyncio
    async def test_patch_project(self, db_session, test_user, request_client):
        pid = await _make_project(db_session, test_user.id)
        await db_session.commit()

        res = request_client.patch(f"/api/v1/projects/{pid}", json={"name": "After"})

        assert res.status_code == 200, res.text
        assert res.json()["name"] == "After"
        assert res.json()["updated_at"]
        async with TestSessionLocal() as fresh:
            stored = await fresh.get(Project, pid)
            assert stored.name == "After"

    @pytest.mark.asyncio
    async def test_patch_design_sheet(self, db_session, test_user, request_client):
        pid = await _make_project(db_session, test_user.id)
        db_session.add(DesignSheet(project_id=pid))
        await db_session.commit()

        res = request_client.patch(f"/api/v1/design-sheet/{pid}", json={"problem": "Slow onboarding"})

        assert res.status_code == 200, res.text
        assert res.json()["problem"] == "Slow onboarding"
        async with TestSessionLocal() as fresh:
            sheet = (
                await fresh.execute(select(DesignSheet).where(DesignSheet.project_id == pid))
            ).scalar_one()
            assert sheet.problem == "Slow onboarding"

    @pytest.mark.asyncio
    async def test_patch_block(self, db_session, test_user, request_client):
        pid = await _make_project(db_session, test_user.id)
        bid = uuid.uuid4()
        db_session.add(Block(id=bid, project_id=pid, name="Login"))
        await db_session.commit()

        res = request_client.patch(f"/api/v1/projects/{pid}/blocks/{bid}", json={"order": 3})

        assert res.status_code == 200, res.text
        assert res.json()["order"] == 3
        async with TestSessionLocal() as fresh:
            assert (await fresh.get(Block, bid)).order == 3

    @pytest.mark.asyncio
    async def test_patch_pipeline_node(self, db_session, test_user, request_client):
        pid = await _make_project(db_session, test_user.id)
        db_session.add(PipelineNode(project_id=pid, layer="frontend", selected_tool="react"))
        await db_session.commit()

        res = request_client.patch(
            f"/api/v1/projects/{pid}/pipeline/frontend", json={"selected_tool": "vue"}
        )

        assert res.status_code == 200, res.text
        assert res.json()["selected_tool"] == "vue"
        async with TestSessionLocal() as fresh:
            node = (
                await fresh.execute(select(PipelineNode).where(PipelineNode.project_id == pid))
            ).scalar_one()
            assert node.selected_tool == "vue"


class TestServerTimestampsAreLoaded:
    """The root cause, checked directly and for every model."""

    @pytest.mark.asyncio
    async def test_updated_at_is_readable_after_an_update(self, db_session, test_user):
        """Sprint generation reads ``plan.updated_at`` right after its last UPDATE."""
        pid = await _make_project(db_session, test_user.id)
        plan = SprintPlan(project_id=pid, user_id=test_user.id, status="generating")
        db_session.add(plan)
        await db_session.commit()

        plan.status = "complete"
        await db_session.flush()
        await db_session.commit()

        # Plain attribute access: no await, so a lazy load here would raise.
        assert plan.updated_at is not None

    def test_every_model_fetches_server_values_on_flush(self):
        """A new model must not be able to bring the fault back."""
        lazy = [m.class_.__name__ for m in Base.registry.mappers if m.eager_defaults is not True]
        assert lazy == []
