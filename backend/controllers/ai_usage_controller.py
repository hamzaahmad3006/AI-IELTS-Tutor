"""AI usage: per-call recording + admin aggregation (SRS section 38)."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.provider import LLMResult
from core.metrics import record_ai_call
from models.ai_interaction import AIInteraction

from .base import CamelModel

# Illustrative price per 1K total tokens (USD). Real pricing is provider/model
# specific and configured later; mock/offline calls cost nothing.
_PRICE_PER_1K = {"groq": 0.0006, "mock": 0.0, "unknown": 0.0}


def _estimate_cost(provider: str, total_tokens: int) -> float:
    rate = _PRICE_PER_1K.get(provider, 0.0)
    return round(rate * total_tokens / 1000.0, 6)


async def record_ai_interaction(
    session: AsyncSession,
    *,
    user_id: str | None,
    feature: str,
    usage: LLMResult,
    status: str = "ok",
) -> None:
    """Persist one AI call. Flushed together with the caller's transaction."""
    cost = _estimate_cost(usage.provider, usage.total_tokens)

    # Mirrored into Prometheus as well as the table: the row is the record of
    # truth and survives a restart, but spend is something you want to be
    # alerted on within a minute rather than discover on an invoice.
    record_ai_call(
        provider=usage.provider,
        feature=feature,
        status=status,
        tokens=usage.total_tokens,
        cost_usd=cost,
    )

    session.add(
        AIInteraction(
            user_id=user_id,
            feature=feature,
            provider=usage.provider,
            model=usage.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=usage.latency_ms,
            cost_usd=cost,
            status=status,
            # Stamped by the orchestrator from the registry, so a score can
            # always be traced to the prompt revision that produced it.
            prompt_id=usage.meta.get("promptId"),
            prompt_version=usage.meta.get("promptVersion"),
        )
    )


# ---------- Admin aggregation ----------
class AIUsageTotals(CamelModel):
    calls: int
    total_tokens: int
    cost_usd: float
    avg_latency_ms: float
    error_rate: float


class AIUsageByModel(CamelModel):
    model: str
    calls: int
    total_tokens: int
    cost_usd: float


class AIUsageResponse(CamelModel):
    feature: str | None
    totals: AIUsageTotals
    by_model: list[AIUsageByModel]


def _day_bounds(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


class AIUsageController:
    @staticmethod
    async def summary(
        session: AsyncSession,
        feature: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> AIUsageResponse:
        filters = []
        if feature:
            filters.append(AIInteraction.feature == feature)
        if date_from:
            filters.append(AIInteraction.created_at >= _day_bounds(date_from))
        if date_to:
            filters.append(AIInteraction.created_at <= _day_bounds(date_to))

        totals_row = (
            await session.execute(
                select(
                    func.count().label("calls"),
                    func.coalesce(func.sum(AIInteraction.total_tokens), 0),
                    func.coalesce(func.sum(AIInteraction.cost_usd), 0.0),
                    func.coalesce(func.avg(AIInteraction.latency_ms), 0.0),
                    func.coalesce(
                        func.sum(
                            case((AIInteraction.status != "ok", 1), else_=0)
                        ),
                        0,
                    ),
                ).where(*filters)
            )
        ).one()
        calls = int(totals_row[0])
        errors = int(totals_row[4])
        totals = AIUsageTotals(
            calls=calls,
            total_tokens=int(totals_row[1]),
            cost_usd=round(float(totals_row[2]), 6),
            avg_latency_ms=round(float(totals_row[3]), 2),
            error_rate=round(errors / calls, 4) if calls else 0.0,
        )

        by_model_rows = (
            await session.execute(
                select(
                    AIInteraction.model,
                    func.count().label("calls"),
                    func.coalesce(func.sum(AIInteraction.total_tokens), 0),
                    func.coalesce(func.sum(AIInteraction.cost_usd), 0.0),
                )
                .where(*filters)
                .group_by(AIInteraction.model)
                .order_by(func.count().desc())
            )
        ).all()
        by_model = [
            AIUsageByModel(
                model=row[0],
                calls=int(row[1]),
                total_tokens=int(row[2]),
                cost_usd=round(float(row[3]), 6),
            )
            for row in by_model_rows
        ]

        return AIUsageResponse(feature=feature, totals=totals, by_model=by_model)
