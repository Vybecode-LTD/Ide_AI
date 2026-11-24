"""
database.py — Async SQLAlchemy engine and session factory.
Provides get_db() async dependency for FastAPI route injection.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=(settings.ENVIRONMENT == "development"),
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models.

    ``eager_defaults`` makes every flush read server-generated values back
    with the statement itself (RETURNING on PostgreSQL). Without it, an
    UPDATE leaves ``updated_at`` (``onupdate=func.now()``) expired, and a
    route that returns the object fails while the response is serialized:
    the lazy load runs outside the async context, raises ``MissingGreenlet``,
    and ``get_db`` rolls the edit back. A model that sets its own
    ``__mapper_args__`` must keep this key
    (``tests/test_request_scoped_writes.py`` checks every model).
    """

    __mapper_args__ = {"eager_defaults": True}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
