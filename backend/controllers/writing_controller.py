"""Writing controller: schemas + scoring business logic."""

from __future__ import annotations

import re

from fastapi import HTTPException, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator, ScoringError
from models.attempt import WritingAttempt
from models.user import User

from .base import CamelModel


class WritingSubmitRequest(CamelModel):
    essay_text: str = Field(min_length=1, max_length=8000)
    task_type: int = Field(default=2, ge=1, le=2)
    prompt_text: str | None = None


class WritingCriteria(CamelModel):
    task_response: float
    coherence_cohesion: float
    lexical_resource: float
    grammatical_range: float


class WritingResultResponse(CamelModel):
    attempt_id: str
    status: str
    task_type: int
    word_count: int
    overall_band: float | None
    criteria: WritingCriteria | None
    feedback_summary: str | None
    improved_essay: str | None


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z']+", text))


def _to_response(attempt: WritingAttempt) -> WritingResultResponse:
    criteria: WritingCriteria | None = None
    if attempt.overall_band is not None:
        criteria = WritingCriteria(
            task_response=attempt.task_response or 0.0,
            coherence_cohesion=attempt.coherence_cohesion or 0.0,
            lexical_resource=attempt.lexical_resource or 0.0,
            grammatical_range=attempt.grammatical_range or 0.0,
        )
    return WritingResultResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        task_type=attempt.task_type,
        word_count=attempt.word_count,
        overall_band=attempt.overall_band,
        criteria=criteria,
        feedback_summary=attempt.feedback_summary,
        improved_essay=attempt.improved_essay,
    )


class WritingController:
    @staticmethod
    async def submit(
        session: AsyncSession,
        user: User,
        orchestrator: AIOrchestrator,
        payload: WritingSubmitRequest,
    ) -> WritingResultResponse:
        attempt = WritingAttempt(
            user_id=user.id,
            task_type=payload.task_type,
            prompt_text=payload.prompt_text,
            essay_text=payload.essay_text,
            word_count=_word_count(payload.essay_text),
            status="scoring",
        )
        session.add(attempt)
        await session.flush()

        try:
            score, usage = await orchestrator.score_writing(
                essay=payload.essay_text, task_type=payload.task_type
            )
        except ScoringError as exc:
            attempt.status = "failed"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Scoring failed: {exc}",
            ) from exc

        attempt.overall_band = score.overall_band
        attempt.task_response = score.task_response
        attempt.coherence_cohesion = score.coherence_cohesion
        attempt.lexical_resource = score.lexical_resource
        attempt.grammatical_range = score.grammatical_range
        attempt.feedback_summary = score.feedback_summary
        attempt.improved_essay = score.improved_essay
        attempt.ai_provider = usage.provider
        attempt.ai_model = usage.model
        attempt.total_tokens = usage.total_tokens
        attempt.status = "scored"
        await session.flush()
        return _to_response(attempt)

    @staticmethod
    async def get(
        session: AsyncSession, user: User, attempt_id: str
    ) -> WritingResultResponse:
        attempt = await session.scalar(
            select(WritingAttempt).where(WritingAttempt.id == attempt_id)
        )
        if attempt is None or attempt.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found"
            )
        return _to_response(attempt)
