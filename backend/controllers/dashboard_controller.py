"""Dashboard controller: composes the real Home overview from stored data.

Matches the DashboardData shape the React Native Home screen already expects
(greeting, streak, band prediction, module levels, coach message, checklist)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.predictor import round_half
from models.attempt import WritingAttempt
from models.listening import ListeningAttempt
from models.profile import LearnerProfile
from models.reading import ReadingAttempt
from models.speaking import SpeakingAttempt
from core.time_on_task import total_minutes
from models.user import User

from .analytics_controller import AnalyticsController
from .base import CamelModel

_MODULE_LABELS = {
    "speaking": "Speaking",
    "writing": "Writing",
    "reading": "Reading",
    "listening": "Listening",
}
_ATTEMPT_MODELS = (WritingAttempt, SpeakingAttempt, ReadingAttempt, ListeningAttempt)


# ---------- Schemas (camelCase to the client) ----------
class BandPrediction(CamelModel):
    predicted_band: float
    confidence: float
    distance_to_target: float
    based_on_sessions: int
    progress_to_target: float


class DailyCoachMessage(CamelModel):
    id: str
    title: str
    message: str


class ModuleProgress(CamelModel):
    module: str
    current_level: float
    is_active: bool


class ChecklistItem(CamelModel):
    id: str
    title: str
    subtitle: str
    is_completed: bool
    completed_at: str | None
    priority: str | None


class StudyTime(CamelModel):
    """Minutes actually spent, not attempts counted.

    Attempt counts flatter: five two-minute taps look like more work than one
    forty-minute essay. Minutes are what a learner is actually budgeting.
    """

    today_minutes: int
    week_minutes: int
    total_minutes: int
    #: Against the daily goal set at onboarding. Capped at 100 so a long day
    #: reads as "done" rather than "247%", which sounds like a warning.
    daily_goal_minutes: int
    daily_goal_pct: int


class DashboardData(CamelModel):
    greeting_name: str
    streak_days: int
    study_time: StudyTime
    prediction: BandPrediction
    coach: DailyCoachMessage
    modules: list[ModuleProgress]
    checklist: list[ChecklistItem]
    checklist_completion_pct: int


# ---------- Helpers ----------
async def _activity_dates(session: AsyncSession, user_id: str) -> set[date]:
    dates: set[date] = set()
    for model in _ATTEMPT_MODELS:
        rows = await session.scalars(
            select(model.created_at).where(model.user_id == user_id)
        )
        for created_at in rows:
            ts = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
            dates.add(ts.date())
    return dates


async def _study_time(
    session: AsyncSession, user_id: str, daily_goal: int
) -> StudyTime:
    """Sum recorded durations across every module.

    Zero-duration rows are included in the sum and cost nothing: attempts made
    before time was tracked genuinely have no measurement, and excluding them
    would make no difference to a total they contribute nothing to.
    """
    now = datetime.now(tz=timezone.utc)
    today = now.date()
    week_start = today - timedelta(days=6)

    total = 0
    this_week = 0
    todays = 0

    for model in _ATTEMPT_MODELS:
        rows = await session.execute(
            select(model.created_at, model.duration_sec).where(
                model.user_id == user_id
            )
        )
        for created_at, seconds in rows.all():
            seconds = int(seconds or 0)
            total += seconds
            ts = (
                created_at
                if created_at.tzinfo
                else created_at.replace(tzinfo=timezone.utc)
            )
            if ts.date() >= week_start:
                this_week += seconds
            if ts.date() == today:
                todays += seconds

    today_minutes = total_minutes(todays)
    goal = max(1, daily_goal)
    return StudyTime(
        today_minutes=today_minutes,
        week_minutes=total_minutes(this_week),
        total_minutes=total_minutes(total),
        daily_goal_minutes=daily_goal,
        # Capped: "247% of your goal" reads like a warning rather than praise.
        daily_goal_pct=min(100, round(today_minutes / goal * 100)),
    )


def _streak(dates: set[date]) -> int:
    """Consecutive active days, anchored on today or yesterday.

    Anchoring on today alone would report 0 for someone with a 30-day run who
    simply has not practised yet today - at 00:01 their streak would appear
    broken. A streak is only lost once a full day has been missed.
    """
    if not dates:
        return 0
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    if today in dates:
        cursor = today
    elif yesterday in dates:
        cursor = yesterday
    else:
        return 0

    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _longest_streak(dates: set[date]) -> int:
    """Longest consecutive run ever recorded, for a personal best."""
    if not dates:
        return 0
    best = run = 1
    ordered = sorted(dates)
    for previous, current in zip(ordered, ordered[1:]):
        run = run + 1 if (current - previous).days == 1 else 1
        best = max(best, run)
    return best


class DashboardController:
    @staticmethod
    async def overview(session: AsyncSession, user: User) -> DashboardData:
        profile = await session.scalar(
            select(LearnerProfile).where(LearnerProfile.user_id == user.id)
        )
        target = profile.target_band if profile else 7.0

        progress = await AnalyticsController.progress(session, user)
        prediction = await AnalyticsController.prediction(session, user)

        current_by_module = {m.module: m.current_band for m in progress.modules}
        predicted_overall = prediction.predicted_overall or progress.overall_band or 0.0

        # Weakest module with data drives the coach + active tile.
        with_data = {m: b for m, b in current_by_module.items() if b is not None}
        weakest = min(with_data, key=lambda m: with_data[m]) if with_data else "speaking"

        distance = round_half(max(0.0, target - predicted_overall))
        progress_to_target = (
            max(0.0, min(1.0, predicted_overall / target)) if target > 0 else 0.0
        )

        band_prediction = BandPrediction(
            predicted_band=predicted_overall,
            confidence=prediction.confidence,
            distance_to_target=distance,
            based_on_sessions=progress.total_attempts,
            progress_to_target=round(progress_to_target, 2),
        )

        if with_data:
            coach_msg = (
                f"Great consistency! Let's focus on {_MODULE_LABELS[weakest]} today "
                f"to close the gap to your Band {target:g} goal."
            )
        else:
            coach_msg = (
                "Welcome! Complete a practice in any module and I'll start tracking "
                "your progress and predicting your band."
            )
        coach = DailyCoachMessage(id="coach_daily", title="Daily Coach", message=coach_msg)

        modules: list[ModuleProgress] = []
        baselines = (
            {
                "speaking": profile.baseline_speaking,
                "writing": profile.baseline_writing,
                "reading": profile.baseline_reading,
                "listening": profile.baseline_listening,
            }
            if profile
            else {}
        )
        for module_name in _MODULE_LABELS:
            level = current_by_module.get(module_name)
            if level is None:
                level = baselines.get(module_name) or 0.0
            modules.append(
                ModuleProgress(
                    module=module_name,
                    current_level=level,
                    is_active=(module_name == weakest),
                )
            )

        # Recommendation checklist (until the study planner lands). An item is
        # marked complete if the learner already practiced that area today.
        today = datetime.now(timezone.utc).date()
        dates_by_module = await _activity_dates(session, user.id)
        practiced_today = today in dates_by_module
        checklist = [
            ChecklistItem(
                id="rec_weak",
                title=f"{_MODULE_LABELS[weakest]} practice session",
                subtitle="Priority: High",
                is_completed=practiced_today,
                completed_at=today.isoformat() if practiced_today else None,
                priority="high",
            ),
            ChecklistItem(
                id="rec_writing",
                title="1 Writing Task 2 essay",
                subtitle="~20 min",
                is_completed=False,
                completed_at=None,
                priority="medium",
            ),
            ChecklistItem(
                id="rec_vocab",
                title="Vocabulary review",
                subtitle="15 min session",
                is_completed=False,
                completed_at=None,
                priority=None,
            ),
        ]
        completed = sum(1 for item in checklist if item.is_completed)
        pct = round(completed / len(checklist) * 100)

        first_name = (user.full_name or "there").split(" ")[0]
        return DashboardData(
            greeting_name=first_name,
            streak_days=_streak(dates_by_module),
            study_time=await _study_time(
                session, user.id, profile.daily_minutes if profile else 30
            ),
            prediction=band_prediction,
            coach=coach,
            modules=modules,
            checklist=checklist,
            checklist_completion_pct=pct,
        )
