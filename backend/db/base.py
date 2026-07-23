"""SQLAlchemy declarative base + shared column mixins."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    # A Python-side default (with microsecond precision) is used in addition to
    # server_default so that ORM inserts get monotonic, precisely-ordered
    # timestamps. This keeps keyset (cursor) pagination correct even for rows
    # created within the same second — SQLite's CURRENT_TIMESTAMP has only
    # second granularity, which otherwise breaks (created_at, id) ordering.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        onupdate=_utcnow,
        nullable=False,
    )
