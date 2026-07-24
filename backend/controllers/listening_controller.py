"""Listening controller: clip delivery, answer auto-grading, band mapping."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.band_mapping import listening_band
from models.content import AudioClip, ListeningQuestion
from models.listening import ListeningAttempt
from models.user import User

from .adaptive_controller import resolve_difficulty
from .base import CamelModel
from .grading import is_correct
from .weakness_controller import WeaknessService


# ---------- Schemas ----------
class ListeningQuestionPublic(CamelModel):
    id: str
    type: str
    prompt: str
    options: list[str] | None = None


class ClipResponse(CamelModel):
    id: str
    title: str
    audio_url: str
    duration_sec: int
    exam_type: str
    difficulty: str
    accent: str | None
    questions: list[ListeningQuestionPublic]


class ListeningSubmitRequest(CamelModel):
    audio_id: str
    answers: dict[str, Any]


class ListeningPerQuestion(CamelModel):
    question_id: str
    type: str
    correct: bool
    submitted: Any
    correct_answer: Any
    explanation: str | None
    answer_timestamp: str | None


class ListeningResultResponse(CamelModel):
    attempt_id: str
    audio_id: str
    raw_score: int
    total_questions: int
    band: float
    per_question: list[ListeningPerQuestion]


# ---------- Seeding (dev/demo content) ----------
_SEED_TRANSCRIPT = (
    "Welcome to the university orientation. The library is open from nine in the "
    "morning until ten at night on weekdays. To borrow books you will need your "
    "student card. The main computer lab is located on the second floor of the "
    "science building. If you have any questions, you can email the support team "
    "at help@university.edu."
)


async def _ensure_seeded(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(AudioClip))
    if count and count > 0:
        return
    clip = AudioClip(
        title="University Orientation",
        object_key="seed/audio/orientation.mp3",
        transcript=_SEED_TRANSCRIPT,
        duration_sec=45,
        exam_type="academic",
        difficulty="medium",
        accent="British",
        source="seed",
    )
    session.add(clip)
    await session.flush()
    session.add_all(
        [
            ListeningQuestion(
                audio_id=clip.id,
                order_index=1,
                type="short_answer",
                prompt="What do you need to borrow books?",
                options=None,
                correct_answer="student card",
                explanation="The speaker says you need your student card to borrow books.",
                answer_timestamp="00:12-00:16",
                difficulty="medium",
            ),
            ListeningQuestion(
                audio_id=clip.id,
                order_index=2,
                type="mcq",
                prompt="Where is the main computer lab located?",
                options=[
                    "First floor of the library",
                    "Second floor of the science building",
                    "Ground floor of the arts building",
                    "Third floor of the science building",
                ],
                correct_answer="Second floor of the science building",
                explanation="The lab is on the second floor of the science building.",
                answer_timestamp="00:20-00:26",
                difficulty="medium",
            ),
            ListeningQuestion(
                audio_id=clip.id,
                order_index=3,
                type="form_completion",
                prompt="The library closes at ____ on weekdays.",
                options=None,
                correct_answer="ten",
                explanation="The library is open until ten at night on weekdays.",
                answer_timestamp="00:06-00:10",
                difficulty="medium",
            ),
        ]
    )
    await session.flush()


class ListeningController:
    @staticmethod
    async def _questions(
        session: AsyncSession, audio_id: str
    ) -> list[ListeningQuestion]:
        rows = await session.scalars(
            select(ListeningQuestion)
            .where(ListeningQuestion.audio_id == audio_id)
            .order_by(ListeningQuestion.order_index)
        )
        return list(rows)

    @classmethod
    async def get_clip(
        cls,
        session: AsyncSession,
        user_id: str,
        difficulty: str | None,
        exam_type: str,
    ) -> ClipResponse:
        await _ensure_seeded(session)
        if difficulty is None or difficulty == "adaptive":
            difficulty, _, _ = await resolve_difficulty(session, user_id, "listening")
        clip = await session.scalar(
            select(AudioClip)
            .where(AudioClip.exam_type == exam_type, AudioClip.difficulty == difficulty)
            .limit(1)
        )
        if clip is None:
            clip = await session.scalar(
                select(AudioClip).where(AudioClip.exam_type == exam_type).limit(1)
            )
        if clip is None:
            clip = await session.scalar(select(AudioClip).limit(1))
        if clip is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No audio available"
            )
        questions = await cls._questions(session, clip.id)
        return ClipResponse(
            id=clip.id,
            title=clip.title,
            # Placeholder; replaced by a signed object-store URL later.
            audio_url=f"/media/{clip.object_key}",
            duration_sec=clip.duration_sec,
            exam_type=clip.exam_type,
            difficulty=clip.difficulty,
            accent=clip.accent,
            questions=[
                ListeningQuestionPublic(
                    id=q.id, type=q.type, prompt=q.prompt, options=q.options
                )
                for q in questions
            ],
        )

    @classmethod
    def _grade(
        cls, questions: list[ListeningQuestion], answers: dict[str, Any]
    ) -> tuple[int, list[ListeningPerQuestion]]:
        raw = 0
        per_question: list[ListeningPerQuestion] = []
        for q in questions:
            submitted = answers.get(q.id)
            correct = is_correct(submitted, q.correct_answer)
            if correct:
                raw += 1
            per_question.append(
                ListeningPerQuestion(
                    question_id=q.id,
                    type=q.type,
                    correct=correct,
                    submitted=submitted,
                    correct_answer=q.correct_answer,
                    explanation=q.explanation,
                    answer_timestamp=q.answer_timestamp,
                )
            )
        return raw, per_question

    @classmethod
    async def submit(
        cls, session: AsyncSession, user: User, payload: ListeningSubmitRequest
    ) -> ListeningResultResponse:
        clip = await session.get(AudioClip, payload.audio_id)
        if clip is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found"
            )
        questions = await cls._questions(session, clip.id)
        total = len(questions)
        raw, per_question = cls._grade(questions, payload.answers)
        band = listening_band(raw, total)

        attempt = ListeningAttempt(
            user_id=user.id,
            audio_id=clip.id,
            answers=payload.answers,
            raw_score=raw,
            total_questions=total,
            band=band,
        )
        session.add(attempt)
        wrong_tags = list(
            dict.fromkeys(pq.type for pq in per_question if not pq.correct)
        )
        if wrong_tags:
            await WeaknessService.record(session, user.id, "listening", wrong_tags)
        await session.flush()
        return ListeningResultResponse(
            attempt_id=attempt.id,
            audio_id=clip.id,
            raw_score=raw,
            total_questions=total,
            band=band,
            per_question=per_question,
        )

    @classmethod
    async def get_attempt(
        cls, session: AsyncSession, user: User, attempt_id: str
    ) -> ListeningResultResponse:
        attempt = await session.get(ListeningAttempt, attempt_id)
        if attempt is None or attempt.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found"
            )
        questions = await cls._questions(session, attempt.audio_id)
        _, per_question = cls._grade(questions, attempt.answers)
        return ListeningResultResponse(
            attempt_id=attempt.id,
            audio_id=attempt.audio_id,
            raw_score=attempt.raw_score,
            total_questions=attempt.total_questions,
            band=attempt.band,
            per_question=per_question,
        )
