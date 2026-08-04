"""Study plan generation.

Deliberately deterministic rather than AI-generated. A study plan has to be
explainable — "why am I doing three Writing sessions this week?" deserves a real
answer — and it must not change every time it is regenerated. The inputs are the
learner's own numbers: distance from target per module, recorded weaknesses, the
time they said they can give, and how long they have.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.analytics_controller import MODULES, _module_points
from core.predictor import round_half
from core.errors import NotFoundError, PreconditionError
from db.repository import OwnedRepository
from models.plan import PlanTask, StudyPlan
from models.profile import LearnerProfile
from models.user import User
from models.weakness import Weakness

from .base import CamelModel

logger = logging.getLogger("api.planner")

_plans = OwnedRepository(StudyPlan, label="Study plan")

MODULE_LABELS = {
    "speaking": "Speaking",
    "writing": "Writing",
    "reading": "Reading",
    "listening": "Listening",
}

#: Horizon when no exam date is set. Long enough to be a plan, short enough to
#: stay meaningful.
DEFAULT_WEEKS = 4
MAX_WEEKS = 12
#: Sessions scheduled per week, spread across modules by need.
SESSIONS_PER_WEEK = 5


class PlanTaskOut(CamelModel):
    id: str
    week: int
    module: str
    title: str
    detail: str
    minutes: int
    priority: float
    is_done: bool


class StudyPlanOut(CamelModel):
    id: str
    target_band: float
    exam_date: date | None
    daily_minutes: int
    weeks: int
    rationale: str
    tasks: list[PlanTaskOut]
    completed_count: int
    total_count: int


def _weeks_until(exam_date: date | None) -> int:
    if exam_date is None:
        return DEFAULT_WEEKS
    days = (exam_date - datetime.now(timezone.utc).date()).days
    if days <= 0:
        # The exam has passed or is today; still give something to work with
        # rather than an empty plan.
        return 1
    return max(1, min(MAX_WEEKS, -(-days // 7)))


def _to_out(plan: StudyPlan, tasks: list[PlanTask]) -> StudyPlanOut:
    return StudyPlanOut(
        id=plan.id,
        target_band=plan.target_band,
        exam_date=plan.exam_date,
        daily_minutes=plan.daily_minutes,
        weeks=plan.weeks,
        rationale=plan.rationale,
        tasks=[
            PlanTaskOut(
                id=t.id,
                week=t.week,
                module=t.module,
                title=t.title,
                detail=t.detail,
                minutes=t.minutes,
                priority=round(t.priority, 3),
                is_done=t.is_done,
            )
            for t in tasks
        ],
        completed_count=sum(1 for t in tasks if t.is_done),
        total_count=len(tasks),
    )


class PlannerController:
    @staticmethod
    async def get_active(session: AsyncSession, user: User) -> StudyPlanOut | None:
        plan = await session.scalar(
            select(StudyPlan)
            .where(StudyPlan.user_id == user.id, StudyPlan.is_active.is_(True))
            .order_by(StudyPlan.created_at.desc())
            .limit(1)
        )
        if plan is None:
            return None
        tasks = (
            await session.execute(
                select(PlanTask)
                .where(PlanTask.plan_id == plan.id)
                .order_by(PlanTask.week, PlanTask.priority.desc())
            )
        ).scalars().all()
        return _to_out(plan, list(tasks))

    @staticmethod
    async def generate(session: AsyncSession, user: User) -> StudyPlanOut:
        profile = await session.scalar(
            select(LearnerProfile).where(LearnerProfile.user_id == user.id)
        )
        if profile is None:
            raise PreconditionError("Complete onboarding before generating a plan")

        target = profile.target_band
        weeks = _weeks_until(profile.exam_date)

        # ---- How far each module is from target ----
        gaps: dict[str, float] = {}
        current: dict[str, float | None] = {}
        for module in MODULES:
            points = await _module_points(session, user.id, module)
            band = points[-1][1] if points else _baseline_for(profile, module)
            current[module] = band
            # An unmeasured module is treated as a full-width gap: it is the
            # least-known thing about the learner, so it earns attention rather
            # than being skipped for having no data.
            gaps[module] = (target - band) if band is not None else max(1.0, target - 4.0)

        # ---- Weakness tags sharpen what each session should focus on ----
        weaknesses = (
            await session.execute(
                select(Weakness)
                .where(Weakness.user_id == user.id, Weakness.resolved.is_(False))
                .order_by(Weakness.severity.desc())
            )
        ).scalars().all()
        top_tag: dict[str, str] = {}
        for w in weaknesses:
            top_tag.setdefault(w.module, w.tag)

        # ---- Allocate sessions proportionally to the gaps ----
        positive = {m: max(0.0, g) for m, g in gaps.items()}
        total_gap = sum(positive.values())
        if total_gap <= 0:
            # Already at or above target everywhere: keep it ticking over
            # evenly rather than producing an empty plan.
            positive = {m: 1.0 for m in MODULES}
            total_gap = float(len(MODULES))

        minutes = max(10, profile.daily_minutes)

        # Deactivate any previous plan; superseded plans are kept for history.
        await session.execute(
            update(StudyPlan)
            .where(StudyPlan.user_id == user.id, StudyPlan.is_active.is_(True))
            .values(is_active=False)
        )

        exam_clause = (
            f"{weeks} week{'s' if weeks != 1 else ''} until your exam"
            if profile.exam_date
            else f"a {weeks}-week block (no exam date set)"
        )
        rationale = (
            f"Built for {exam_clause}, {minutes} minutes a day, targeting band "
            f"{target:.1f}. Sessions are weighted towards the modules furthest "
            f"from your target."
        )

        plan = StudyPlan(
            user_id=user.id,
            target_band=target,
            exam_date=profile.exam_date,
            daily_minutes=minutes,
            weeks=weeks,
            rationale=rationale,
        )
        session.add(plan)
        await session.flush()

        tasks: list[PlanTask] = []
        for week in range(1, weeks + 1):
            # Largest-remainder allocation, so the weekly total is exactly
            # SESSIONS_PER_WEEK instead of drifting with rounding.
            exact = {m: positive[m] / total_gap * SESSIONS_PER_WEEK for m in MODULES}
            counts = {m: int(v) for m, v in exact.items()}
            remaining = SESSIONS_PER_WEEK - sum(counts.values())
            for module, _ in sorted(
                exact.items(), key=lambda kv: kv[1] - int(kv[1]), reverse=True
            )[:remaining]:
                counts[module] += 1

            for module, count in counts.items():
                for _ in range(count):
                    tag = top_tag.get(module)
                    focus = tag.replace("_", " ") if tag else "overall fluency"
                    band = current[module]
                    detail = (
                        f"Focus on {focus}. "
                        + (
                            f"You are at band {band:.1f}, {round_half(max(0.0, target - band)):.1f} from target."
                            if band is not None
                            else "No score recorded yet — this session establishes one."
                        )
                    )
                    tasks.append(
                        PlanTask(
                            plan_id=plan.id,
                            week=week,
                            module=module,
                            title=f"{MODULE_LABELS[module]} practice",
                            detail=detail,
                            minutes=minutes,
                            priority=round(gaps[module], 3),
                        )
                    )

        session.add_all(tasks)
        await session.flush()

        logger.info(
            "study plan generated",
            extra={"userId": user.id, "weeks": weeks, "tasks": len(tasks)},
        )
        return _to_out(plan, tasks)

    @staticmethod
    async def complete_task(
        session: AsyncSession, user: User, task_id: str, done: bool
    ) -> PlanTaskOut:
        task = await session.scalar(select(PlanTask).where(PlanTask.id == task_id))
        if task is None:
            raise NotFoundError("Task not found")
        # Ownership runs through the plan rather than trusting the task id.
        # A plan belonging to someone else raises NotFound too, so the id is
        # never confirmed to a stranger.
        await _plans.get_owned(session, task.plan_id, user.id)

        task.is_done = done
        return PlanTaskOut(
            id=task.id,
            week=task.week,
            module=task.module,
            title=task.title,
            detail=task.detail,
            minutes=task.minutes,
            priority=round(task.priority, 3),
            is_done=task.is_done,
        )


def _baseline_for(profile: LearnerProfile, module: str) -> float | None:
    """Fall back to the diagnostic baseline before any attempts exist."""
    return {
        "speaking": profile.baseline_speaking,
        "writing": profile.baseline_writing,
        "reading": profile.baseline_reading,
        "listening": profile.baseline_listening,
    }.get(module)
