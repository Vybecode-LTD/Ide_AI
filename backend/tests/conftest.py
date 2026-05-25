"""
conftest.py — Shared fixtures for backend tests.

Provides an async in-memory SQLite database and test user for unit/integration
tests that exercise SQLAlchemy models and service logic.

Usage:
    pytest tests/ -v
"""
import os
import uuid

# Set minimal env vars BEFORE importing app modules (settings reads on import).
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ANTHROPIC_KEY", "test-key-not-real")

import json

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from app.core.database import Base
from app.models.user import User

# ---------------------------------------------------------------------------
# SQLite compatibility: JSONB → JSON, PostgreSQL UUID → CHAR(32)
# ---------------------------------------------------------------------------
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(PG_UUID, "sqlite")
def _compile_pg_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"

# Import all models so Base.metadata knows every table.
import app.models.project  # noqa: F401
import app.models.session  # noqa: F401
import app.models.design_sheet  # noqa: F401
import app.models.block  # noqa: F401
import app.models.pipeline_node  # noqa: F401
import app.models.prompt_kit  # noqa: F401
import app.models.market_analysis  # noqa: F401
import app.models.sprint_plan  # noqa: F401
import app.models.version  # noqa: F401
import app.models.user_memory  # noqa: F401
import app.models.project_share  # noqa: F401
import app.models.share_comment  # noqa: F401
import app.models.share_rating  # noqa: F401
import app.models.idea_inbox  # noqa: F401
import app.models.concept_branch  # noqa: F401
import app.models.external_integration  # noqa: F401
import app.models.project_template  # noqa: F401
import app.models.module_pathway  # noqa: F401
import app.models.module_response  # noqa: F401
import app.models.project_snapshot  # noqa: F401
import app.models.admin_audit_log  # noqa: F401

# ---------------------------------------------------------------------------
# Engine + session factory (in-memory SQLite, one per test session)
# ---------------------------------------------------------------------------
TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    future=True,
)


def _jsonb_array_length(value):
    """SQLite UDF that emulates PostgreSQL's jsonb_array_length()."""
    if value is None:
        return None
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        return len(parsed) if isinstance(parsed, list) else 0
    except (json.JSONDecodeError, TypeError):
        return 0


@event.listens_for(TEST_ENGINE.sync_engine, "connect")
def _register_sqlite_functions(dbapi_conn, connection_record):
    """Register PostgreSQL-equivalent functions for SQLite testing."""
    dbapi_conn.create_function("jsonb_array_length", 1, _jsonb_array_length)
TestSessionLocal = async_sessionmaker(
    TEST_ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Create all tables before each test, drop after."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Yields a fresh async session for each test."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Creates and returns a test user persisted in the DB."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
        display_name="Tester",
        email_verified=True,
        account_type="free",
    )
    db_session.add(user)
    await db_session.flush()
    return user
