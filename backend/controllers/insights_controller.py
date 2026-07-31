"""Learning insights: strengths, weaknesses and practice consistency.

Everything here is derived from attempts the learner actually made. Nothing is
estimated or padded — where a number is not measured it is reported as such
rather than invented, because a fabricated "hours studied" is worse than no
figure at all.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.analytics_controller import MODULES, _module_points
from controllers.dashboard_controller import (
    _ATTEMPT_MODELS,
    _activity_dates,
    _longest_streak,
    _streak,
)
from core.predictor import round_half
from models.speaking import SpeakingAttempt
from models.user import User
from models.weakness import Weakness

from .base import CamelModel

MODULE_LABELS = {
    "speaking": "Speaking",
    "writing": "Writing",
    "reading": "Reading",
    "listening": "Listening",
}

#: Weeks of history in the activity histogram.
ACTIVITY_WEEKS = 8
#: Window for the "active days" figure.
RECENT_WINDOW_DAYS = 30


#: Tags whose title-cased form reads badly in prose ("mcq", "True False
#: Notgiven"). Anything not listed falls back to title case.
_TAG_LABELS = {
    "mcq": "multiple choice",
    "true_false_notgiven": "True/False/Not Given",
    "short_answer": "short answer",
    "grammatical_range": "grammatical range",
    "lexical_resource": "lexical resource",
    "task_response": "task response",
    "coherence_cohesion": "coherence and cohesion",
    "fluency_coherence": "fluency and coherence",
    "pronunciation": "pronunciation",
}


def _pretty_tag(tag: str) -> str:
    return _TAG_LABELS.get(tag, tag.replace("_", " ").title())


async def _attempt_timestamps(session: AsyncSession, user_id: str) -> list[date]:
    """Date of every attempt, NOT deduplicated.

    `_activity_dates` returns a set, which is right for streaks but would turn
    an attempt count into a day count.
    """
    stamps: list[date] = []
    for model in _ATTEMPT_MODELS:
        rows = await session.scalars(
            select(model.created_at).where(model.user_id == user_id)
        )
        for created_at in rows:
            ts = (
                created_at
                if created_at.tzinfo
                else created_at.replace(tzinfo=timezone.utc)
            )
            stamps.append(ts.date())
    return stamps


class StrengthCard(CamelModel):
    module: str
    label: str
    band: float
    detail: str


class WeaknessCard(CamelModel):
    module: str
    label: str
    tag: str
    tag_label: str
    severity: float
    occurrences: int
    detail: str


class WeekActivity(CamelModel):
    #: Monday of the week, ISO date.
    week_start: date
    attempts: int
    active_days: int


class ConsistencyStats(CamelModel):
    current_streak: int
    longest_streak: int
    active_days_last30: int
    total_attempts: int
    weeks: list[WeekActivity]
    #: Speaking is the only module that records real elapsed time, so it is the
    #: only time reported. Null when nothing has been recorded.
    measured_speaking_minutes: int | None
    time_note: str


class InsightsResponse(CamelModel):
    strengths: list[StrengthCard]
    weaknesses: list[WeaknessCard]
    consistency: ConsistencyStats
    summary: str


class InsightsController:
    @staticmethod
    async def insights(session: AsyncSession, user: User) -> InsightsResponse:
        # ---- Strengths: modules ranked by current band ----
        current: dict[str, float] = {}
        attempts_per_module: dict[str, int] = {}
        for module in MODULES:
            points = await _module_points(session, user.id, module)
            attempts_per_module[module] = len(points)
            if points:
                current[module] = points[-1][1]

        ranked = sorted(current.items(), key=lambda kv: kv[1], reverse=True)
        average = round_half(sum(current.values()) / len(current)) if current else None

        strengths: list[StrengthCard] = []
        for module, band in ranked[:2]:
            if average is not None and band >= average:
                delta = round(band - average, 1)
                detail = (
                    f"{delta:+.1f} above your overall band"
                    if delta
                    else "level with your overall band"
                )
            else:
                detail = "your highest scoring module"
            strengths.append(
                StrengthCard(
                    module=module,
                    label=MODULE_LABELS.get(module, module),
                    band=band,
                    detail=detail,
                )
            )

        # ---- Weaknesses: recorded skill tags, worst first ----
        rows = (
            await session.execute(
                select(Weakness)
                .where(Weakness.user_id == user.id, Weakness.resolved.is_(False))
                .order_by(Weakness.severity.desc())
                .limit(4)
            )
        ).scalars().all()

        weaknesses = [
            WeaknessCard(
                module=w.module,
                label=MODULE_LABELS.get(w.module, w.module),
                tag=w.tag,
                tag_label=_pretty_tag(w.tag),
                severity=round(w.severity, 2),
                occurrences=w.occurrences,
                detail=(
                    f"Seen {w.occurrences} time{'s' if w.occurrences != 1 else ''} "
                    f"in {MODULE_LABELS.get(w.module, w.module)}"
                ),
            )
            for w in rows
        ]

        # ---- Consistency ----
        dates = await _activity_dates(session, user.id)
        stamps = await _attempt_timestamps(session, user.id)
        today = datetime.now(timezone.utc).date()
        recent_cutoff = today - timedelta(days=RECENT_WINDOW_DAYS)

        # Weeks run Monday-Sunday, oldest first.
        this_monday = today - timedelta(days=today.weekday())
        weeks: list[WeekActivity] = []
        for offset in range(ACTIVITY_WEEKS - 1, -1, -1):
            start = this_monday - timedelta(weeks=offset)
            end = start + timedelta(days=6)
            weeks.append(
                WeekActivity(
                    week_start=start,
                    attempts=sum(1 for d in stamps if start <= d <= end),
                    active_days=len({d for d in dates if start <= d <= end}),
                )
            )

        speaking_seconds = await session.scalar(
            select(func.sum(SpeakingAttempt.duration_sec)).where(
                SpeakingAttempt.user_id == user.id
            )
        )
        speaking_minutes = (
            round(speaking_seconds / 60) if speaking_seconds else None
        )

        consistency = ConsistencyStats(
            current_streak=_streak(dates),
            longest_streak=_longest_streak(dates),
            active_days_last30=len({d for d in dates if d > recent_cutoff}),
            total_attempts=sum(attempts_per_module.values()),
            weeks=weeks,
            measured_speaking_minutes=speaking_minutes,
            time_note=(
                "Only spoken responses are timed, so this covers Speaking only."
            ),
        )

        # ---- Plain-language summary ----
        if not current:
            summary = (
                "Complete a practice in any module and your strengths and focus "
                "areas will appear here."
            )
        elif weaknesses:
            best = strengths[0]
            worst = weaknesses[0]
            summary = (
                f"{best.label} is carrying you at band {best.band}. "
                f"Your biggest drag is {worst.tag_label.lower()} in "
                f"{worst.label.lower()}."
            )
        else:
            best = strengths[0]
            summary = (
                f"{best.label} leads at band {best.band}, and nothing is flagged "
                "as a weakness yet. Keep practising to sharpen the picture."
            )

        return InsightsResponse(
            strengths=strengths,
            weaknesses=weaknesses,
            consistency=consistency,
            summary=summary,
        )
