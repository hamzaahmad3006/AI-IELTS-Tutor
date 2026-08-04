"""Smoke test: retention sweeps, and the indexes migration 0018 adds.

The sweep deletes data, so the tests that matter are the ones about what it
leaves alone: rows inside the window, aggregate usage figures, and everything at
all when nobody asked for a real run.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_retention.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from sqlalchemy import func, inspect, select  # noqa: E402

from core.retention import RetentionPolicy, sweep  # noqa: E402
from db.session import SessionLocal, engine  # noqa: E402
from models.ai_interaction import AIInteraction  # noqa: E402
from db.base import Base  # noqa: E402
from models.user import RefreshToken, User  # noqa: E402
from models.weakness import Weakness  # noqa: E402

NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)

#: (name, table) pairs migration 0018 introduces.
EXPECTED_INDEXES = [
    ("ix_writing_attempts_user_created", "writing_attempts"),
    ("ix_speaking_attempts_user_created", "speaking_attempts"),
    ("ix_reading_attempts_user_created", "reading_attempts"),
    ("ix_listening_attempts_user_created", "listening_attempts"),
    ("ix_ai_interactions_user_created", "ai_interactions"),
    ("ix_ai_interactions_created", "ai_interactions"),
    ("ix_refresh_tokens_expires", "refresh_tokens"),
    ("ix_weaknesses_user_resolved", "weaknesses"),
]


def check_policy_validation() -> None:
    RetentionPolicy()  # the defaults must be self-consistent

    # Deleting before anonymising would make the anonymise window unreachable,
    # so an operator's "90 day" setting would silently be a delete-everything
    # setting. That has to fail loudly at configuration time.
    for kwargs in (
        {"ai_anonymise_after_days": 90, "ai_delete_after_days": 30},
        {"ai_anonymise_after_days": 90, "ai_delete_after_days": 90},
        {"refresh_grace_days": -1},
    ):
        try:
            RetentionPolicy(**kwargs)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"{kwargs} should have been rejected")


async def _seed(session) -> str:
    user = User(
        full_name="Retention Subject",
        email="retention@example.com",
        password_hash="x",
    )
    session.add(user)
    await session.flush()

    def interaction(days_ago: int) -> AIInteraction:
        return AIInteraction(
            user_id=user.id,
            feature="writing",
            provider="mock",
            model="mock-heuristic",
            total_tokens=100,
            cost_usd=0.01,
            created_at=NOW - timedelta(days=days_ago),
        )

    session.add_all(
        [
            interaction(1),  # fresh: untouched
            interaction(89),  # just inside the anonymise window: untouched
            interaction(91),  # past it: anonymised
            interaction(400),  # past it: anonymised
            interaction(800),  # past the delete window: removed
        ]
    )
    session.add_all(
        [
            RefreshToken(
                user_id=user.id,
                token_hash="live",
                expires_at=NOW + timedelta(days=10),
            ),
            RefreshToken(
                user_id=user.id,
                token_hash="recent",
                expires_at=NOW - timedelta(days=2),  # expired, still in grace
            ),
            RefreshToken(
                user_id=user.id,
                token_hash="ancient",
                expires_at=NOW - timedelta(days=60),
            ),
        ]
    )
    session.add_all(
        [
            Weakness(
                user_id=user.id,
                module="writing",
                tag="active_issue",
                severity=0.6,
                resolved=False,
                last_seen_at=NOW - timedelta(days=400),  # old but unresolved
            ),
            Weakness(
                user_id=user.id,
                module="writing",
                tag="old_resolved",
                severity=0.1,
                resolved=True,
                last_seen_at=NOW - timedelta(days=400),
            ),
            Weakness(
                user_id=user.id,
                module="speaking",
                tag="recent_resolved",
                severity=0.1,
                resolved=True,
                last_seen_at=NOW - timedelta(days=10),
            ),
        ]
    )
    await session.commit()
    return user.id


async def check_sweep() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        await _seed(session)

        total_cost = await session.scalar(select(func.sum(AIInteraction.cost_usd)))

        # A dry run reports and changes nothing.
        dry = await sweep(session, now=NOW, apply=False)
        assert dry.applied is False
        assert (dry.ai_anonymised, dry.ai_deleted) == (2, 1), dry
        assert (dry.refresh_deleted, dry.weaknesses_deleted) == (1, 1), dry
        assert dry.total == 5
        assert "DRY RUN" in dry.describe()

        assert await session.scalar(select(func.count()).select_from(AIInteraction)) == 5
        assert await session.scalar(select(func.count()).select_from(RefreshToken)) == 3
        assert await session.scalar(select(func.count()).select_from(Weakness)) == 3

        # The real run does exactly what the dry run said it would.
        applied = await sweep(session, now=NOW, apply=True)
        assert applied.applied is True
        assert applied.ai_anonymised == dry.ai_anonymised
        assert applied.ai_deleted == dry.ai_deleted
        assert applied.refresh_deleted == dry.refresh_deleted
        assert applied.weaknesses_deleted == dry.weaknesses_deleted
        assert "APPLIED" in applied.describe()

    async with SessionLocal() as session:
        rows = list(await session.scalars(select(AIInteraction)))
        assert len(rows) == 4, "only the row past the delete window should be gone"

        # Two rows lost their owner; the two inside the window kept theirs.
        assert sum(1 for r in rows if r.user_id is None) == 2
        assert sum(1 for r in rows if r.user_id is not None) == 2

        # Cost survives anonymisation. This is the point of nulling the user
        # rather than deleting the row: usage reporting must not develop a hole
        # every time the retention job runs.
        for r in rows:
            assert r.cost_usd == 0.01 and r.total_tokens == 100
        remaining = await session.scalar(select(func.sum(AIInteraction.cost_usd)))
        assert abs(remaining - (total_cost - 0.01)) < 1e-9, (remaining, total_cost)

        hashes = set(await session.scalars(select(RefreshToken.token_hash)))
        assert hashes == {"live", "recent"}, hashes

        tags = set(await session.scalars(select(Weakness.tag)))
        assert tags == {"active_issue", "recent_resolved"}, tags

        # Idempotent: running again finds nothing left to do.
        again = await sweep(session, now=NOW, apply=True)
        assert again.total == 0, again


async def check_indexes() -> None:
    """Every index 0018 declares exists on the table it names.

    Built here from the models rather than by running alembic, so this checks
    the schema the app actually uses. The migration is exercised separately by
    the upgrade/downgrade step in CI.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        found = await conn.run_sync(
            lambda sync_conn: {
                table: {i["name"] for i in inspect(sync_conn).get_indexes(table)}
                for table in {t for _, t in EXPECTED_INDEXES}
            }
        )

    for name, table in EXPECTED_INDEXES:
        assert name in found[table], f"{name} missing from {table}: {found[table]}"


def run() -> None:
    check_policy_validation()
    asyncio.run(check_sweep())
    asyncio.run(check_indexes())

    print("RETENTION SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
