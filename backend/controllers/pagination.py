"""Keyset (cursor) pagination helper shared by the history endpoints.

Cursor encodes the last row's (created_at, id) so pages are stable even as new
rows are inserted (SRS section 17.1)."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any, Sequence, TypeVar

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

MAX_LIMIT = 50
DEFAULT_LIMIT = 20


def encode_cursor(created_at: datetime, row_id: str) -> str:
    raw = f"{created_at.isoformat()}|{row_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_str, row_id = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), row_id


def clamp_limit(limit: int) -> int:
    return max(1, min(MAX_LIMIT, limit))


async def paginate(
    session: AsyncSession,
    model: type[T],
    conditions: Sequence[Any],
    cursor: str | None,
    limit: int,
) -> tuple[list[T], str | None]:
    """Return (items, next_cursor) ordered by created_at DESC, id DESC."""
    limit = clamp_limit(limit)
    stmt = select(model).where(*conditions)
    if cursor:
        ts, last_id = decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                model.created_at < ts,  # type: ignore[attr-defined]
                and_(
                    model.created_at == ts,  # type: ignore[attr-defined]
                    model.id < last_id,  # type: ignore[attr-defined]
                ),
            )
        )
    stmt = stmt.order_by(
        model.created_at.desc(),  # type: ignore[attr-defined]
        model.id.desc(),  # type: ignore[attr-defined]
    ).limit(limit + 1)

    rows = list(await session.scalars(stmt))
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor: str | None = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.created_at, last.id)  # type: ignore[attr-defined]
    return items, next_cursor
