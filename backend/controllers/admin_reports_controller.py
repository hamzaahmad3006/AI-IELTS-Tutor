"""Platform reports: how things are changing, rather than what they are now.

The admin overview answers "how many". This answers "is that going up", which a
snapshot cannot, and which is the only version of the question anyone actually
acts on.

Three reports, chosen because each one can change a decision:

* **Daily activity** — signups, active learners, attempts and spend per day.
  Shows growth or decay, and shows spend tracking usage or not.
* **Band distribution** — where learners actually sit. A scorer that has drifted
  shows up here as a lump in the wrong place long before anyone complains.
* **Retention** — whether people come back. Everything else can look healthy
  while nobody returns after their first session.

Every figure is a count over real rows. Nothing is extrapolated: a dashboard
that estimates is worse than one that only reports what it can measure, because
the estimate is indistinguishable from the measurement once it is on a chart.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_interaction import AIInteraction
from models.attempt import WritingAttempt
from models.listening import ListeningAttempt
from models.reading import ReadingAttempt
from models.speaking import SpeakingAttempt
from models.user import User

from .base import CamelModel

_ATTEMPT_MODELS = (
    ("writing", WritingAttempt),
    ("speaking", SpeakingAttempt),
    ("reading", ReadingAttempt),
    ("listening", ListeningAttempt),
)

#: Default reporting window. Long enough to see a trend, short enough that the
#: chart is readable on a phone.
DEFAULT_DAYS = 30
MAX_DAYS = 365

#: Band buckets. Half-band granularity would produce eighteen columns that all
#: look the same; these are the boundaries people actually talk about.
BAND_BUCKETS = [
    ("below 5.0", 0.0, 5.0),
    ("5.0 - 5.5", 5.0, 6.0),
    ("6.0 - 6.5", 6.0, 7.0),
    ("7.0 - 7.5", 7.0, 8.0),
    ("8.0+", 8.0, 9.1),
]


class DailyPoint(CamelModel):
    day: date
    new_users: int
    active_learners: int
    attempts: int
    ai_cost_usd: float


class BandBucket(CamelModel):
    label: str
    count: int
    #: Share of all scored attempts, as a percentage. Reported alongside the
    #: count because a bucket of 40 means nothing without the total.
    share_pct: float


class RetentionPoint(CamelModel):
    #: Days since the learner registered.
    day_offset: int
    #: Learners whose account is at least this old -- the denominator.
    eligible: int
    #: How many of those were active on or after that day.
    returned: int
    rate_pct: float


class PlatformReports(CamelModel):
    window_days: int
    daily: list[DailyPoint]
    bands: list[BandBucket]
    retention: list[RetentionPoint]
    generated_at: datetime


def _as_date(value: datetime) -> date:
    return (
        value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    ).date()


class AdminReportsController:
    @staticmethod
    async def reports(
        session: AsyncSession, days: int = DEFAULT_DAYS
    ) -> PlatformReports:
        days = max(1, min(days, MAX_DAYS))
        now = datetime.now(tz=timezone.utc)
        today = now.date()
        start = today - timedelta(days=days - 1)
        since = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)

        # ---------- Daily activity ----------
        new_users: dict[date, int] = defaultdict(int)
        for created_at in await session.scalars(
            select(User.created_at).where(User.created_at >= since)
        ):
            new_users[_as_date(created_at)] += 1

        attempts: dict[date, int] = defaultdict(int)
        active: dict[date, set[str]] = defaultdict(set)
        for _, model in _ATTEMPT_MODELS:
            rows = await session.execute(
                select(model.created_at, model.user_id).where(
                    model.created_at >= since
                )
            )
            for created_at, user_id in rows.all():
                day = _as_date(created_at)
                attempts[day] += 1
                # A set per day, not a count: someone practising four modules
                # is one active learner, and summing per-module counts would
                # quadruple them.
                active[day].add(user_id)

        cost: dict[date, float] = defaultdict(float)
        rows = await session.execute(
            select(AIInteraction.created_at, AIInteraction.cost_usd).where(
                AIInteraction.created_at >= since
            )
        )
        for created_at, amount in rows.all():
            cost[_as_date(created_at)] += float(amount or 0.0)

        # Every day in the window, including empty ones. Omitting quiet days
        # compresses the axis and makes a gap look like continuous activity.
        daily = [
            DailyPoint(
                day=start + timedelta(days=offset),
                new_users=new_users.get(start + timedelta(days=offset), 0),
                active_learners=len(active.get(start + timedelta(days=offset), ())),
                attempts=attempts.get(start + timedelta(days=offset), 0),
                ai_cost_usd=round(cost.get(start + timedelta(days=offset), 0.0), 4),
            )
            for offset in range(days)
        ]

        # ---------- Band distribution ----------
        counts = [0] * len(BAND_BUCKETS)
        total_scored = 0
        for _, model in _ATTEMPT_MODELS:
            band_column = getattr(model, "band", None) or getattr(
                model, "overall_band", None
            )
            if band_column is None:
                continue
            for band in await session.scalars(
                select(band_column).where(band_column.is_not(None))
            ):
                value = float(band)
                total_scored += 1
                for index, (_, low, high) in enumerate(BAND_BUCKETS):
                    if low <= value < high:
                        counts[index] += 1
                        break

        bands = [
            BandBucket(
                label=label,
                count=counts[index],
                share_pct=round(counts[index] / total_scored * 100, 1)
                if total_scored
                else 0.0,
            )
            for index, (label, _, _) in enumerate(BAND_BUCKETS)
        ]

        # ---------- Retention ----------
        registered: dict[str, date] = {}
        for user_id, created_at in (
            await session.execute(select(User.id, User.created_at))
        ).all():
            registered[user_id] = _as_date(created_at)

        last_active: dict[str, date] = {}
        for _, model in _ATTEMPT_MODELS:
            rows = await session.execute(
                select(model.user_id, func.max(model.created_at)).group_by(
                    model.user_id
                )
            )
            for user_id, latest in rows.all():
                day = _as_date(latest)
                if user_id not in last_active or day > last_active[user_id]:
                    last_active[user_id] = day

        retention: list[RetentionPoint] = []
        for offset in (1, 3, 7, 14, 30):
            # Only accounts old enough to have had the chance. Including a
            # learner who registered yesterday in the 30-day figure counts them
            # as churned for a month they have not lived through, which drags
            # every cohort down and makes retention look worse the faster you
            # grow.
            eligible = [
                user_id
                for user_id, joined in registered.items()
                if (today - joined).days >= offset
            ]
            returned = sum(
                1
                for user_id in eligible
                if user_id in last_active
                and (last_active[user_id] - registered[user_id]).days >= offset
            )
            retention.append(
                RetentionPoint(
                    day_offset=offset,
                    eligible=len(eligible),
                    returned=returned,
                    rate_pct=round(returned / len(eligible) * 100, 1)
                    if eligible
                    else 0.0,
                )
            )

        return PlatformReports(
            window_days=days,
            daily=daily,
            bands=bands,
            retention=retention,
            generated_at=now,
        )
