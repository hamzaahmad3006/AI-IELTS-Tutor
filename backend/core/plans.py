"""Plans and what they entitle a learner to.

This is the half of "subscription management" that is worth building now.
Payments need a provider, a merchant account and a compliance conversation;
usage limits need none of that and solve a problem the project already has --
AI calls cost real money, and nothing currently stops one learner spending all
of it.

Limits are counted per calendar month over `ai_interactions`, which is already
written on every scoring call. No new counter, no cache to fall out of sync
with the truth, and a limit that is computed from the billing record cannot
disagree with the bill.

Two things are deliberately not limited.

Reading and listening are graded by comparing answers to a key -- no model is
involved and no money is spent, so capping them would restrict practice for no
reason. Only the AI-scored modules count against a plan.

And a learner who reaches their limit keeps everything they have already done:
history, progress, weaknesses, plans. Locking someone out of their own past
work because they practised too much this month would be a strange punishment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import AppError
from models.ai_interaction import AIInteraction


class Plan(str, Enum):
    FREE = "free"
    PLUS = "plus"
    UNLIMITED = "unlimited"

    @classmethod
    def parse(cls, raw: str | None) -> Plan:
        """Unknown or missing resolves to free.

        Failing to the *least* generous plan: a typo in a plan name must not
        hand someone unlimited AI, and the worst case of getting it wrong this
        way is a support message rather than a bill.
        """
        try:
            return cls((raw or "").strip().lower())
        except ValueError:
            return cls.FREE


@dataclass(frozen=True)
class Entitlements:
    plan: Plan
    #: AI-scored attempts per calendar month. None means no limit.
    monthly_ai_attempts: int | None
    #: Whether the spoken interview is available. It is the most expensive
    #: feature per session -- transcription plus synthesis plus scoring.
    spoken_interview: bool
    label: str


ENTITLEMENTS: dict[Plan, Entitlements] = {
    # Enough to genuinely evaluate the app -- a few essays and speaking
    # attempts a week. A free tier that runs out on day two is a trial, not a
    # free tier, and people uninstall rather than upgrade.
    Plan.FREE: Entitlements(
        plan=Plan.FREE,
        monthly_ai_attempts=30,
        spoken_interview=False,
        label="Free",
    ),
    Plan.PLUS: Entitlements(
        plan=Plan.PLUS,
        monthly_ai_attempts=300,
        spoken_interview=True,
        label="Plus",
    ),
    # For staff and anyone comped. Distinct from a very high number so the
    # intent is readable in the data.
    Plan.UNLIMITED: Entitlements(
        plan=Plan.UNLIMITED,
        monthly_ai_attempts=None,
        spoken_interview=True,
        label="Unlimited",
    ),
}

#: Features that spend money. Reading and listening are graded against an
#: answer key, so they are free to run and are not counted.
BILLED_FEATURES = ("writing", "speaking", "interview", "diagnostic")


class PlanLimitReached(AppError):
    """The learner has used their allowance for this month."""

    status = 402
    code = "plan_limit_reached"
    title = "Monthly limit reached"


class FeatureNotInPlan(AppError):
    """The plan does not include this feature at all."""

    status = 402
    code = "feature_not_in_plan"
    title = "Not included in your plan"


def entitlements_for(plan: str | None) -> Entitlements:
    return ENTITLEMENTS[Plan.parse(plan)]


def month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(tz=timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def used_this_month(
    session: AsyncSession, user_id: str, *, now: datetime | None = None
) -> int:
    """AI-scored attempts this calendar month.

    Counted from ai_interactions rather than from a separate counter, so the
    number a learner is shown is the same one the bill is computed from. Failed
    calls are excluded: charging someone for a scoring attempt that errored is
    charging them for our outage.
    """
    return (
        await session.scalar(
            select(func.count())
            .select_from(AIInteraction)
            .where(
                AIInteraction.user_id == user_id,
                AIInteraction.created_at >= month_start(now),
                AIInteraction.status == "ok",
                AIInteraction.feature.in_(BILLED_FEATURES),
            )
        )
        or 0
    )


@dataclass(frozen=True)
class UsageSummary:
    plan: str
    label: str
    used: int
    limit: int | None
    remaining: int | None
    spoken_interview: bool


async def usage_for(
    session: AsyncSession, user_id: str, plan: str | None
) -> UsageSummary:
    entitlements = entitlements_for(plan)
    used = await used_this_month(session, user_id)
    limit = entitlements.monthly_ai_attempts
    return UsageSummary(
        plan=entitlements.plan.value,
        label=entitlements.label,
        used=used,
        limit=limit,
        # Never negative. A learner shown "-3 remaining" reads it as a debt.
        remaining=None if limit is None else max(0, limit - used),
        spoken_interview=entitlements.spoken_interview,
    )


async def require_capacity(
    session: AsyncSession, user_id: str, plan: str | None, *, feature: str
) -> None:
    """Raise unless this learner may make another billed call.

    Checked before the work starts, not after. Scoring an essay and then
    refusing to show the result would spend the money and deliver nothing,
    which is the worst of both.
    """
    entitlements = entitlements_for(plan)

    if feature == "interview" and not entitlements.spoken_interview:
        raise FeatureNotInPlan(
            f"The spoken interview is not included in the {entitlements.label} "
            f"plan."
        )

    limit = entitlements.monthly_ai_attempts
    if limit is None:
        return

    used = await used_this_month(session, user_id)
    if used >= limit:
        raise PlanLimitReached(
            f"You have used all {limit} AI-scored attempts on the "
            f"{entitlements.label} plan this month. Your allowance resets on "
            f"the 1st. Reading and listening practice are unaffected."
        )
