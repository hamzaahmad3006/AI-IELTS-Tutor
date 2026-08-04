"""Admin dashboard: platform KPIs and the registered prompt versions.

Every figure is a straight count over real rows. Nothing is estimated or
extrapolated: an operations dashboard that guesses is worse than one that only
reports what it can actually measure.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.prompts import all_templates
from models.ai_interaction import AIInteraction
from models.attempt import WritingAttempt
from models.listening import ListeningAttempt
from models.mock_test import MockTest
from models.plan import StudyPlan
from models.profile import LearnerProfile
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

ACTIVE_WINDOW_DAYS = 7


class ModuleCount(CamelModel):
    module: str
    attempts: int


class PromptInfo(CamelModel):
    id: str
    version: str
    description: str


class AdminOverview(CamelModel):
    total_users: int
    onboarded_users: int
    #: Distinct learners with at least one attempt in the last 7 days. Named
    #: for how it serialises: `active_users_7d` becomes `activeUsers7D`,
    #: which reads like a typo in the API.
    active_learners_last_week: int
    total_attempts: int
    attempts_by_module: list[ModuleCount]
    mock_tests_completed: int
    active_study_plans: int
    ai_calls: int
    ai_tokens: int
    ai_cost_usd: float
    ai_failures: int
    #: Which prompt versions are live, so a scoring change can be dated.
    prompts: list[PromptInfo]
    generated_at: datetime


class AdminOverviewController:
    @staticmethod
    async def overview(session: AsyncSession) -> AdminOverview:
        since = datetime.now(tz=timezone.utc) - timedelta(days=ACTIVE_WINDOW_DAYS)

        total_users = await session.scalar(select(func.count()).select_from(User)) or 0
        onboarded = (
            await session.scalar(select(func.count()).select_from(LearnerProfile))
            or 0
        )

        by_module: list[ModuleCount] = []
        total_attempts = 0
        active_ids: set[str] = set()
        for name, model in _ATTEMPT_MODELS:
            count = (
                await session.scalar(select(func.count()).select_from(model)) or 0
            )
            by_module.append(ModuleCount(module=name, attempts=count))
            total_attempts += count

            # Counted per model then unioned in Python: a learner active in two
            # modules is one active user, not two.
            recent = await session.scalars(
                select(model.user_id).where(model.created_at >= since).distinct()
            )
            active_ids.update(recent)

        mock_tests = (
            await session.scalar(
                select(func.count())
                .select_from(MockTest)
                .where(MockTest.status == "completed")
            )
            or 0
        )
        active_plans = (
            await session.scalar(
                select(func.count())
                .select_from(StudyPlan)
                .where(StudyPlan.is_active.is_(True))
            )
            or 0
        )

        ai_calls = (
            await session.scalar(select(func.count()).select_from(AIInteraction)) or 0
        )
        ai_tokens = (
            await session.scalar(select(func.sum(AIInteraction.total_tokens))) or 0
        )
        ai_cost = await session.scalar(select(func.sum(AIInteraction.cost_usd))) or 0.0
        ai_failures = (
            await session.scalar(
                select(func.count())
                .select_from(AIInteraction)
                .where(AIInteraction.status != "ok")
            )
            or 0
        )

        return AdminOverview(
            total_users=total_users,
            onboarded_users=onboarded,
            active_learners_last_week=len(active_ids),
            total_attempts=total_attempts,
            attempts_by_module=by_module,
            mock_tests_completed=mock_tests,
            active_study_plans=active_plans,
            ai_calls=ai_calls,
            ai_tokens=int(ai_tokens),
            ai_cost_usd=round(float(ai_cost), 4),
            ai_failures=ai_failures,
            prompts=[
                PromptInfo(
                    id=t.id, version=t.version, description=t.description
                )
                for t in all_templates()
            ],
            generated_at=datetime.now(tz=timezone.utc),
        )
