"""Admin content generation.

Generated items land as drafts rather than going live. A model asked for an
IELTS passage will occasionally produce something subtly wrong -- a question
with two defensible answers, a "Not Given" that is arguably "False" -- and a
learner marked wrong by a broken question learns the wrong lesson and stops
trusting the app. A human approves before anyone practises against it.

Admin-only and batch-capped, because unlike scoring this has no natural ceiling:
nothing about the request stops someone asking for a thousand passages, and each
one is a billed call.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ai.generation import MAX_BATCH, GenerationRequest, prompt_kwargs
from ai.orchestrator import AIOrchestrator, ScoringError
from core.errors import ValidationError
from models.user import User

from .ai_usage_controller import record_ai_interaction
from .base import CamelModel


class GenerateRequest(CamelModel):
    kind: str
    count: int = 1
    difficulty: str = "medium"
    topic: str = ""
    exam_type: str = "academic"
    part: int = 1
    task_type: int = 2


class GeneratedItem(CamelModel):
    kind: str
    #: The item itself, shaped by its schema. Returned as-is for review rather
    #: than flattened, so a reviewer sees exactly what would be stored.
    item: dict[str, Any]
    prompt_id: str | None = None
    prompt_version: str | None = None


class GenerateResponse(CamelModel):
    requested: int
    generated: list[GeneratedItem]
    #: Items that failed to generate or parse, with the reason. Reported rather
    #: than silently dropped: five drafts from a request for ten is a different
    #: situation from ten, and the caller paid for both.
    failures: list[str]
    tokens_used: int
    estimated_cost_usd: float


class ContentGenerationController:
    @staticmethod
    async def generate(
        session: AsyncSession,
        user: User,
        orchestrator: AIOrchestrator,
        payload: GenerateRequest,
    ) -> GenerateResponse:
        try:
            request = GenerationRequest(
                kind=payload.kind,
                count=payload.count,
                difficulty=payload.difficulty,
                topic=payload.topic,
                exam_type=payload.exam_type,
                part=payload.part,
                task_type=payload.task_type,
            ).validated()
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        generated: list[GeneratedItem] = []
        failures: list[str] = []
        tokens = 0
        cost = 0.0

        for index in range(request.count):
            try:
                item, usage = await orchestrator.generate_content(
                    kind=request.kind, **prompt_kwargs(request)
                )
            except (ScoringError, ValueError) as exc:
                # One bad item does not abandon the batch: the caller asked for
                # ten and nine usable drafts is a better outcome than none.
                failures.append(f"item {index + 1}: {exc}")
                continue

            tokens += usage.total_tokens
            await record_ai_interaction(
                session,
                user_id=user.id,
                feature=f"generate.{request.kind}",
                usage=usage,
            )
            generated.append(
                GeneratedItem(
                    kind=request.kind,
                    item=item.model_dump(),
                    prompt_id=usage.meta.get("promptId"),
                    prompt_version=usage.meta.get("promptVersion"),
                )
            )

        await session.commit()

        return GenerateResponse(
            requested=request.count,
            generated=generated,
            failures=failures,
            tokens_used=tokens,
            estimated_cost_usd=round(cost, 6),
        )


__all__ = [
    "ContentGenerationController",
    "GenerateRequest",
    "GenerateResponse",
    "MAX_BATCH",
]
