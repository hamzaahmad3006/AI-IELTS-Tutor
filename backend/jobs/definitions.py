"""The jobs themselves.

Each is a thin adapter over work that already exists elsewhere, so the schedule
and the behaviour stay separate: retention rules live in core.retention, decay
lives in the weakness controller, and this module only decides how often.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from controllers.weakness_controller import WeaknessService
from core.retention import sweep

from .scheduler import PeriodicJob


async def _retention(session: AsyncSession) -> str:
    """Apply the retention policy for real.

    `apply=True` here, unlike the CLI, which defaults to a dry run. A scheduled
    job that only ever simulates would let data accumulate forever while
    reporting that it was being cleaned.
    """
    report = await sweep(session, apply=True)
    return (
        f"anonymised {report.ai_anonymised}, deleted {report.ai_deleted} usage rows; "
        f"removed {report.refresh_deleted} tokens, "
        f"{report.weaknesses_deleted} resolved weaknesses"
    )


async def _weakness_decay(session: AsyncSession) -> str:
    """Age out weaknesses nobody has repeated.

    Without this, severity only ever rises: a mistake made once in January
    would still be flagged as a top weakness in June, and the recommendations
    built from it would be about a problem the learner has already fixed.
    """
    updated = await WeaknessService.apply_decay(session)
    await session.commit()
    return f"decayed {updated} weaknesses"


#: Daily, and offset from each other only by the order they are listed. Both
#: are cheap and neither contends with the other.
JOBS = [
    PeriodicJob(
        name="weakness_decay",
        interval=timedelta(days=1),
        run=_weakness_decay,
        description="Age out weaknesses that have not recurred.",
    ),
    PeriodicJob(
        name="retention",
        interval=timedelta(days=1),
        run=_retention,
        description="Anonymise and remove data past its retention window.",
    ),
]
