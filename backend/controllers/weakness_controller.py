"""Weakness memory: record recurring weaknesses, list them, decay stale ones.

Feeds adaptive difficulty + recommendations (SRS section 25 & 27). Severity
rises with a saturating increase on recurrence and decays over time."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.weakness import Weakness

from .base import CamelModel

BETA = 0.25  # saturating-increase factor
DECAY_LAMBDA = 0.05  # per-day decay
RECENCY_LAMBDA = 0.08  # per-day recency weighting for prioritization
RESOLVE_BELOW = 0.1

# Weak if a scored criterion falls below this band.
WEAK_BAND_THRESHOLD = 6.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def criteria_below_threshold(criteria: dict[str, float]) -> list[str]:
    """Return criterion keys scoring below the weakness threshold."""
    return [key for key, band in criteria.items() if band < WEAK_BAND_THRESHOLD]


# ---------- Schemas ----------
class WeaknessItem(CamelModel):
    module: str
    tag: str
    severity: float
    occurrences: int
    last_seen_at: datetime
    resolved: bool
    priority: float


class WeaknessListResponse(CamelModel):
    items: list[WeaknessItem]


class WeaknessService:
    @staticmethod
    async def record(
        session: AsyncSession, user_id: str, module: str, tags: list[str]
    ) -> None:
        """Upsert each tag: saturating severity increase, refresh recency."""
        now = _utcnow()
        for tag in tags:
            existing = await session.scalar(
                select(Weakness).where(
                    and_(
                        Weakness.user_id == user_id,
                        Weakness.module == module,
                        Weakness.tag == tag,
                    )
                )
            )
            if existing is None:
                session.add(
                    Weakness(
                        user_id=user_id,
                        module=module,
                        tag=tag,
                        severity=round(BETA, 4),
                        occurrences=1,
                        last_seen_at=now,
                        resolved=False,
                    )
                )
            else:
                existing.severity = round(
                    min(1.0, existing.severity + BETA * (1.0 - existing.severity)), 4
                )
                existing.occurrences += 1
                existing.last_seen_at = now
                existing.resolved = False
        await session.flush()

    @staticmethod
    async def list_for_user(
        session: AsyncSession, user_id: str, include_resolved: bool = False
    ) -> WeaknessListResponse:
        query = select(Weakness).where(Weakness.user_id == user_id)
        if not include_resolved:
            query = query.where(Weakness.resolved.is_(False))
        rows = list(await session.scalars(query))
        now = _utcnow()

        def priority(w: Weakness) -> float:
            days = max(0.0, (now - _aware(w.last_seen_at)).total_seconds() / 86400.0)
            recency = math.exp(-RECENCY_LAMBDA * days)
            return w.severity * recency

        items = sorted(
            (
                WeaknessItem(
                    module=w.module,
                    tag=w.tag,
                    severity=w.severity,
                    occurrences=w.occurrences,
                    last_seen_at=w.last_seen_at,
                    resolved=w.resolved,
                    priority=round(priority(w), 4),
                )
                for w in rows
            ),
            key=lambda i: i.priority,
            reverse=True,
        )
        return WeaknessListResponse(items=items)

    @staticmethod
    async def apply_decay(session: AsyncSession, user_id: str | None = None) -> int:
        """Decay severity by elapsed time; resolve those that fall low.

        Returns the number of weaknesses updated. Intended to run as a daily job.
        """
        query = select(Weakness).where(Weakness.resolved.is_(False))
        if user_id is not None:
            query = query.where(Weakness.user_id == user_id)
        rows = list(await session.scalars(query))
        now = _utcnow()
        updated = 0
        for w in rows:
            days = max(0.0, (now - _aware(w.last_seen_at)).total_seconds() / 86400.0)
            if days <= 0:
                continue
            w.severity = round(w.severity * math.exp(-DECAY_LAMBDA * days), 4)
            if w.severity < RESOLVE_BELOW:
                w.resolved = True
            updated += 1
        await session.flush()
        return updated
