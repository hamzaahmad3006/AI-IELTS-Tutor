"""Async database engine, session factory and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings

_settings = get_settings()

# create_async_engine does not open a connection until first use, so importing
# this module is safe even without a reachable database.
engine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Request-scoped database session."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_models() -> None:
    """Dev convenience: create tables from ORM metadata.

    In production, schema is managed by Alembic migrations instead.
    """
    from db.base import Base
    import models  # noqa: F401  (ensure models are imported/registered)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
