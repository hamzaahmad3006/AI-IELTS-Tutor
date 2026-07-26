"""Speaking controller: transcript scoring business logic + schemas.

Real-time voice capture (LiveKit/STT/TTS) is a later milestone; this scores the
transcript produced at the end of a session."""

from __future__ import annotations

from fastapi import HTTPException, status
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator, ScoringError
from models.cue_card import CueCard
from models.speaking import SpeakingAttempt
from models.user import User

from .ai_usage_controller import record_ai_interaction
from .base import CamelModel
from .weakness_controller import WeaknessService, criteria_below_threshold


class SpeakingSubmitRequest(CamelModel):
    transcript: str = Field(min_length=1, max_length=12000)
    part: int | None = Field(default=None, ge=1, le=3)
    duration_sec: int = Field(default=0, ge=0)


class CueCardResponse(CamelModel):
    id: str
    topic: str
    prompt: str
    bullet_points: list[str]
    difficulty: str
    prep_seconds: int
    speak_seconds: int


# ---------- Cue card bank seeding (dev/demo content) ----------
_SEED_CUE_CARDS: list[dict[str, object]] = [
    {
        "topic": "A memorable place",
        "prompt": "Describe a place you visited that made a lasting impression.",
        "bullet_points": [
            "where it was",
            "when you went there",
            "what you did there",
            "and explain why it made a lasting impression",
        ],
        "difficulty": "medium",
    },
    {
        "topic": "A skill you learned",
        "prompt": "Describe a skill you learned that you are proud of.",
        "bullet_points": [
            "what the skill is",
            "how you learned it",
            "how long it took you",
            "and explain why you are proud of it",
        ],
        "difficulty": "medium",
    },
    {
        "topic": "A person who influenced you",
        "prompt": "Describe a person who has had a significant influence on you.",
        "bullet_points": [
            "who this person is",
            "how you know them",
            "what they have done",
            "and explain how they influenced you",
        ],
        "difficulty": "hard",
    },
]


async def _ensure_cue_cards_seeded(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(CueCard))
    if count and count > 0:
        return
    for row in _SEED_CUE_CARDS:
        session.add(CueCard(**row, source="seed"))
    await session.flush()


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
    async def get_cue_card(
        session: AsyncSession, difficulty: str | None
    ) -> CueCardResponse:
        await _ensure_cue_cards_seeded(session)
        query = select(CueCard)
        if difficulty and difficulty != "adaptive":
            query = query.where(CueCard.difficulty == difficulty)
        # Random pick so repeated practice varies the cue card.
        card = await session.scalar(query.order_by(func.random()).limit(1))
        if card is None:
            card = await session.scalar(
                select(CueCard).order_by(func.random()).limit(1)
            )
        if card is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No cue card available"
            )
        return CueCardResponse(
            id=card.id,
            topic=card.topic,
            prompt=card.prompt,
            bullet_points=list(card.bullet_points),
            difficulty=card.difficulty,
            prep_seconds=card.prep_seconds,
            speak_seconds=card.speak_seconds,
        )

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
        weak_tags = criteria_below_threshold(
            {
                "fluency_coherence": score.fluency_coherence,
                "lexical_resource": score.lexical_resource,
                "grammatical_range": score.grammatical_range,
                "pronunciation": score.pronunciation,
            }
        )
        if weak_tags:
            await WeaknessService.record(session, user.id, "speaking", weak_tags)
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
