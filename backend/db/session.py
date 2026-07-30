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

_IS_POSTGRES = _settings.database_url.startswith("postgresql")

# Managed Postgres (Supabase) sits behind NAT that silently drops idle TCP
# connections. A pooled connection that outlives the idle timeout is dead on
# reuse, and asyncpg surfaces that as a bare OSError ("[WinError 121] The
# semaphore timeout period has expired") which the dialect does not classify as
# a disconnect - so pool_pre_ping alone cannot recover it and the request 500s.
# Recycling connections well inside the idle timeout keeps them from ever
# reaching that state; pre-ping remains as the backstop.
_POSTGRES_OPTIONS: dict[str, object] = {
    "pool_recycle": 300,
    "pool_size": 5,
    "max_overflow": 10,
    "connect_args": {
        # Fail fast on an unreachable host instead of hanging the request.
        "timeout": 10,
        "command_timeout": 30,
        # Server-side statement names break under transaction-mode poolers
        # (Supavisor/pgbouncer); harmless on a direct connection.
        "statement_cache_size": 0,
    },
}

# create_async_engine does not open a connection until first use, so importing
# this module is safe even without a reachable database.
engine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    **(_POSTGRES_OPTIONS if _IS_POSTGRES else {}),
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


async def seed_admin() -> None:
    """Dev/demo: ensure a default admin account exists (SQLite only)."""
    from sqlalchemy import select

    from core.security import hash_password
    from models.user import User

    settings = get_settings()
    async with SessionLocal() as session:
        existing = await session.scalar(
            select(User).where(User.email == settings.seed_admin_email)
        )
        if existing is None:
            session.add(
                User(
                    email=settings.seed_admin_email,
                    password_hash=hash_password(settings.seed_admin_password),
                    full_name="Platform Admin",
                    role="admin",
                    email_verified=True,
                )
            )
            await session.commit()
