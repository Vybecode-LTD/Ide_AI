"""
test_discovery_resume.py — Tests for discovery session resume behavior.

These tests document the desired API behavior for discovery session resumability.
They require a real async database fixture to exercise SQLAlchemy query behavior.

To run: pytest tests/test_discovery_resume.py -v
Requires: pytest, pytest-asyncio, and backend dependencies installed.
"""
import uuid

import pytest

from app.models.project import Project
from app.models.session import DiscoverySession
from app.services.discovery_service import (
    create_or_resume_session,
    create_session,
    get_latest_active_session_for_project,
)

# ---------------------------------------------------------------------------
# NOTE: These tests require db_session and test_user fixtures.
# If those fixtures are not yet available, these tests will be collected
# but will fail with a clear fixture-missing error.
# Add async database fixtures in conftest.py before enabling.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_or_resume_returns_existing_active_session(db_session, test_user):
    """Resuming discovery should return the existing active session, not create a new one."""
    project = Project(
        user_id=test_user.id,
        name="Resume Test",
        description="Test project for resume behavior",
    )
    db_session.add(project)
    await db_session.flush()

    first, created_first = await create_or_resume_session(db_session, project.id)
    await db_session.commit()

    second, created_second = await create_or_resume_session(db_session, project.id)

    assert created_first is True
    assert created_second is False
    assert second.id == first.id


@pytest.mark.asyncio
async def test_create_or_resume_force_new_creates_second_session(db_session, test_user):
    """force_new=True should create a new session even if an active one exists."""
    project = Project(
        user_id=test_user.id,
        name="Force New Test",
        description="Test project for force_new behavior",
    )
    db_session.add(project)
    await db_session.flush()

    first, _ = await create_or_resume_session(db_session, project.id)
    await db_session.commit()

    second, created_second = await create_or_resume_session(
        db_session,
        project.id,
        force_new=True,
    )

    assert created_second is True
    assert second.id != first.id


@pytest.mark.asyncio
async def test_get_latest_active_session_returns_none_for_no_sessions(db_session, test_user):
    """Should return None when no active sessions exist for a project."""
    project = Project(
        user_id=test_user.id,
        name="No Sessions Test",
        description="Test project with no sessions",
    )
    db_session.add(project)
    await db_session.flush()

    result = await get_latest_active_session_for_project(db_session, project.id)
    assert result is None


@pytest.mark.asyncio
async def test_resumed_session_preserves_messages(db_session, test_user):
    """Resumed session should preserve its existing messages."""
    from app.services.discovery_service import add_message

    project = Project(
        user_id=test_user.id,
        name="Message Preserve Test",
        description="Test that messages survive resume",
    )
    db_session.add(project)
    await db_session.flush()

    session, _ = await create_or_resume_session(db_session, project.id)
    await add_message(db_session, session, "assistant", "Hello! Tell me about your idea.")
    await add_message(db_session, session, "user", "I want to build a recipe app.")
    await db_session.commit()

    resumed, created = await create_or_resume_session(db_session, project.id)

    assert created is False
    assert resumed.id == session.id
    assert len(resumed.messages) == 2
    assert resumed.messages[0]["role"] == "assistant"
    assert resumed.messages[1]["role"] == "user"
