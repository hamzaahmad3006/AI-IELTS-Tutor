"""Speaking controller: transcript scoring business logic + schemas.

Real-time voice capture (LiveKit/STT/TTS) is a later milestone; this scores the
transcript produced at the end of a session."""

from __future__ import annotations

from fastapi import HTTPException, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator, ScoringError
from models.speaking import SpeakingAttempt
from models.user import User

from .ai_usage_controller import record_ai_interaction
from .base import CamelModel


class SpeakingSubmitRequest(CamelModel):
    transcript: str = Field(min_length=1, max_length=12000)
    part: int | None = Field(default=None, ge=1, le=3)
    duration_sec: int = Field(default=0, ge=0)


class SpeakingCriteria(CamelModel):
    fluency_coherence: float
    lexical_resource: float
    grammatical_range: float
    pronunciation: float


class SpeakingResultResponse(CamelModel):
    attempt_id: str
    status: str
    part: int | None
    overall_band: float | None
    criteria: SpeakingCriteria | None
    feedback_summary: str | None


def _to_response(attempt: SpeakingAttempt) -> SpeakingResultResponse:
    criteria: SpeakingCriteria | None = None
    if attempt.overall_band is not None:
        criteria = SpeakingCriteria(
            fluency_coherence=attempt.fluency_coherence or 0.0,
            lexical_resource=attempt.lexical_resource or 0.0,
            grammatical_range=attempt.grammatical_range or 0.0,
            pronunciation=attempt.pronunciation or 0.0,
        )
    return SpeakingResultResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        part=attempt.part,
        overall_band=attempt.overall_band,
        criteria=criteria,
        feedback_summary=attempt.feedback_summary,
    )


class SpeakingController:
    @staticmethod
    async def submit(
        session: AsyncSession,
        user: User,
        orchestrator: AIOrchestrator,
        payload: SpeakingSubmitRequest,
    ) -> SpeakingResultResponse:
        attempt = SpeakingAttempt(
            user_id=user.id,
            part=payload.part,
            transcript=payload.transcript,
            duration_sec=payload.duration_sec,
            status="scoring",
        )
        session.add(attempt)
        await session.flush()

        try:
            score, usage = await orchestrator.score_speaking(
                transcript=payload.transcript, part=payload.part
            )
        except ScoringError as exc:
            attempt.status = "failed"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Scoring failed: {exc}",
            ) from exc

        attempt.overall_band = score.overall_band
        attempt.fluency_coherence = score.fluency_coherence
        attempt.lexical_resource = score.lexical_resource
        attempt.grammatical_range = score.grammatical_range
        attempt.pronunciation = score.pronunciation
        attempt.feedback_summary = score.feedback_summary
        attempt.ai_provider = usage.provider
        attempt.ai_model = usage.model
        attempt.total_tokens = usage.total_tokens
        attempt.status = "scored"
        await record_ai_interaction(
            session, user_id=user.id, feature="speaking", usage=usage
        )
        await session.flush()
        return _to_response(attempt)

    @staticmethod
    async def get(
        session: AsyncSession, user: User, attempt_id: str
    ) -> SpeakingResultResponse:
        attempt = await session.scalar(
            select(SpeakingAttempt).where(SpeakingAttempt.id == attempt_id)
        )
        if attempt is None or attempt.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found"
            )
        return _to_response(attempt)
