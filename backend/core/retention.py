"""Data retention sweeps.

Three kinds of row accumulate without bound and none of them should:

* `ai_interactions` -- one per scoring call, holding cost, tokens, latency and
  the learner it belonged to.
* `refresh_tokens` -- expired and revoked credentials that can never be used
  again but stay readable in a backup forever.
* Resolved `weaknesses` -- kept long after they stopped describing anyone.

The interesting decision is the first one. The obvious sweep deletes old rows,
but that also destroys the cost and usage history the admin dashboard reports,
so a month-over-month spend comparison would silently lose its earlier half.

So the sweep separates the two things that age differently. What makes the row
personal is `user_id`; what makes it useful is the tokens, cost and latency.
After the anonymise window the user_id is nulled and the row stays, so aggregate
figures remain correct while the link to a person is gone. Only after a much
longer window is the row deleted outright.

Everything here is a dry run unless explicitly told otherwise. A retention job
is one of the few pieces of code whose entire purpose is destroying data, and it
should have to be asked twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_interaction import AIInteraction
from models.user import RefreshToken
from models.weakness import Weakness

#: Personal linkage is dropped from usage rows after this long.
AI_ANONYMISE_AFTER_DAYS = 90

#: The anonymised rows are deleted after this long. Deliberately much larger:
#: by then they carry no personal data and only cost storage.
AI_DELETE_AFTER_DAYS = 730

#: Expired tokens are kept briefly past expiry so that a support question about
#: a session can still be answered, then removed.
REFRESH_GRACE_DAYS = 7

#: A weakness marked resolved is history, not state.
RESOLVED_WEAKNESS_AFTER_DAYS = 180


@dataclass
class RetentionReport:
    """What a sweep did, or would do. Same shape either way."""

    applied: bool
    ai_anonymised: int
    ai_deleted: int
    refresh_deleted: int
    weaknesses_deleted: int
    cutoffs: dict[str, datetime]

    @property
    def total(self) -> int:
        return (
            self.ai_anonymised
            + self.ai_deleted
            + self.refresh_deleted
            + self.weaknesses_deleted
        )

    def describe(self) -> str:
        verb = "removed" if self.applied else "would remove"
        act = "anonymised" if self.applied else "would anonymise"
        return "\n".join(
            [
                f"Retention sweep ({'APPLIED' if self.applied else 'DRY RUN'})",
                f"  ai_interactions {act}: {self.ai_anonymised}",
                f"  ai_interactions {verb}: {self.ai_deleted}",
                f"  refresh_tokens {verb}: {self.refresh_deleted}",
                f"  resolved weaknesses {verb}: {self.weaknesses_deleted}",
                f"  total affected: {self.total}",
            ]
        )


@dataclass(frozen=True)
class RetentionPolicy:
    ai_anonymise_after_days: int = AI_ANONYMISE_AFTER_DAYS
    ai_delete_after_days: int = AI_DELETE_AFTER_DAYS
    refresh_grace_days: int = REFRESH_GRACE_DAYS
    resolved_weakness_after_days: int = RESOLVED_WEAKNESS_AFTER_DAYS

    def __post_init__(self) -> None:
        # Deleting sooner than anonymising would make the anonymise step
        # unreachable, and the operator would never know their 90-day window was
        # actually a delete-everything window.
        if self.ai_delete_after_days <= self.ai_anonymise_after_days:
            raise ValueError(
                "ai_delete_after_days must be greater than ai_anonymise_after_days; "
                f"got {self.ai_delete_after_days} <= {self.ai_anonymise_after_days}"
            )
        for name, value in vars(self).items():
            if value < 0:
                raise ValueError(f"{name} must not be negative")


async def sweep(
    session: AsyncSession,
    *,
    policy: RetentionPolicy | None = None,
    now: datetime | None = None,
    apply: bool = False,
) -> RetentionReport:
    """Run (or simulate) the retention policy.

    `now` is injectable so the windows can be tested without waiting 90 days.
    Nothing is written unless `apply` is true; the counts are identical either
    way, so a dry run tells you exactly what the real run will do.
    """
    policy = policy or RetentionPolicy()
    now = now or datetime.now(tz=timezone.utc)

    cutoffs = {
        "ai_anonymise": now - timedelta(days=policy.ai_anonymise_after_days),
        "ai_delete": now - timedelta(days=policy.ai_delete_after_days),
        "refresh": now - timedelta(days=policy.refresh_grace_days),
        "weakness": now - timedelta(days=policy.resolved_weakness_after_days),
    }

    # Ordered oldest-window first: a row past the delete cutoff is also past the
    # anonymise cutoff, and counting it under both would overstate the sweep.
    delete_ai = select(func.count()).select_from(AIInteraction).where(
        AIInteraction.created_at < cutoffs["ai_delete"]
    )
    anonymise_ai = (
        select(func.count())
        .select_from(AIInteraction)
        .where(
            AIInteraction.created_at < cutoffs["ai_anonymise"],
            AIInteraction.created_at >= cutoffs["ai_delete"],
            AIInteraction.user_id.is_not(None),
        )
    )
    stale_refresh = select(func.count()).select_from(RefreshToken).where(
        RefreshToken.expires_at < cutoffs["refresh"]
    )
    old_weaknesses = select(func.count()).select_from(Weakness).where(
        Weakness.resolved.is_(True), Weakness.last_seen_at < cutoffs["weakness"]
    )

    ai_deleted = await session.scalar(delete_ai) or 0
    ai_anonymised = await session.scalar(anonymise_ai) or 0
    refresh_deleted = await session.scalar(stale_refresh) or 0
    weaknesses_deleted = await session.scalar(old_weaknesses) or 0

    if apply:
        # synchronize_session=False on every statement: these are set-based
        # sweeps over rows nobody is holding, and the default strategy tries to
        # re-evaluate the WHERE clause against loaded objects -- which compares
        # the driver's naive timestamps against these aware cutoffs and raises.
        bulk = {"synchronize_session": False}
        await session.execute(
            delete(AIInteraction).where(
                AIInteraction.created_at < cutoffs["ai_delete"]
            ),
            execution_options=bulk,
        )
        await session.execute(
            update(AIInteraction)
            .where(
                AIInteraction.created_at < cutoffs["ai_anonymise"],
                AIInteraction.user_id.is_not(None),
            )
            .values(user_id=None),
            execution_options=bulk,
        )
        await session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < cutoffs["refresh"]),
            execution_options=bulk,
        )
        await session.execute(
            delete(Weakness).where(
                Weakness.resolved.is_(True),
                Weakness.last_seen_at < cutoffs["weakness"],
            ),
            execution_options=bulk,
        )
        await session.commit()

    return RetentionReport(
        applied=apply,
        ai_anonymised=ai_anonymised,
        ai_deleted=ai_deleted,
        refresh_deleted=refresh_deleted,
        weaknesses_deleted=weaknesses_deleted,
        cutoffs=cutoffs,
    )
