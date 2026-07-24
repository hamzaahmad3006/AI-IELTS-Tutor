"""Reading controller: passage delivery, answer auto-grading, band mapping."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.band_mapping import reading_band
from models.content import Passage, Question
from models.reading import ReadingAttempt
from models.user import User

from .base import CamelModel
from .grading import is_correct
from .weakness_controller import WeaknessService


# ---------- Schemas ----------
class QuestionPublic(CamelModel):
    id: str
    type: str
    prompt: str
    options: list[str] | None = None


class PassageResponse(CamelModel):
    id: str
    title: str
    body: str
    exam_type: str
    difficulty: str
    topic: str | None
    word_count: int
    questions: list[QuestionPublic]


class ReadingSubmitRequest(CamelModel):
    passage_id: str
    answers: dict[str, Any]


class PerQuestionResult(CamelModel):
    question_id: str
    type: str
    correct: bool
    submitted: Any
    correct_answer: Any
    explanation: str | None


class ReadingResultResponse(CamelModel):
    attempt_id: str
    passage_id: str
    raw_score: int
    total_questions: int
    band: float
    per_question: list[PerQuestionResult]


# ---------- Seeding (dev/demo content) ----------
_SEED_BODY = (
    "Tea is one of the most widely consumed beverages in the world. According to "
    "historical records, tea originated in China, where it was first used as a "
    "medicinal drink thousands of years ago. Over time it spread along trade "
    "routes to the rest of Asia and, eventually, to Europe. The processing of the "
    "leaves determines the type of tea: green tea is barely oxidized, whereas "
    "black tea is produced by allowing the leaves to oxidize fully. Today, tea is "
    "cultivated in dozens of countries and remains central to many cultures."
)


async def _ensure_seeded(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(Passage))
    if count and count > 0:
        return
    passage = Passage(
        title="The History of Tea",
        body=_SEED_BODY,
        exam_type="academic",
        difficulty="medium",
        topic="history",
        word_count=len(_SEED_BODY.split()),
        source="seed",
    )
    session.add(passage)
    await session.flush()
    session.add_all(
        [
            Question(
                passage_id=passage.id,
                order_index=1,
                type="mcq",
                prompt="According to the passage, where did tea originate?",
                options=["India", "China", "Japan", "England"],
                correct_answer="China",
                explanation="The passage states tea originated in China.",
                difficulty="medium",
            ),
            Question(
                passage_id=passage.id,
                order_index=2,
                type="true_false_notgiven",
                prompt="Tea was first used as a medicinal drink.",
                options=["true", "false", "not_given"],
                correct_answer="true",
                explanation="The text says it was first used as a medicinal drink.",
                difficulty="medium",
            ),
            Question(
                passage_id=passage.id,
                order_index=3,
                type="short_answer",
                prompt="Which tea is produced by allowing the leaves to oxidize fully?",
                options=None,
                correct_answer="black",
                explanation="Black tea is produced by full oxidation of the leaves.",
                difficulty="medium",
            ),
        ]
    )
    await session.flush()


class ReadingController:
    @staticmethod
    async def _questions(session: AsyncSession, passage_id: str) -> list[Question]:
        rows = await session.scalars(
            select(Question)
            .where(Question.passage_id == passage_id)
            .order_by(Question.order_index)
        )
        return list(rows)

    @classmethod
    async def get_passage(
        cls, session: AsyncSession, difficulty: str | None, exam_type: str
    ) -> PassageResponse:
        await _ensure_seeded(session)
        query = select(Passage).where(Passage.exam_type == exam_type)
        if difficulty:
            query = query.where(Passage.difficulty == difficulty)
        passage = await session.scalar(query.limit(1))
        if passage is None:
            passage = await session.scalar(select(Passage).limit(1))
        if passage is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No passages available"
            )
        questions = await cls._questions(session, passage.id)
        return PassageResponse(
            id=passage.id,
            title=passage.title,
            body=passage.body,
            exam_type=passage.exam_type,
            difficulty=passage.difficulty,
            topic=passage.topic,
            word_count=passage.word_count,
            questions=[
                QuestionPublic(
                    id=q.id,
                    type=q.type,
                    prompt=q.prompt,
                    options=q.options,
                )
                for q in questions
            ],
        )

    @classmethod
    async def _grade(
        cls, questions: list[Question], answers: dict[str, Any]
    ) -> tuple[int, list[PerQuestionResult]]:
        raw = 0
        per_question: list[PerQuestionResult] = []
        for q in questions:
            submitted = answers.get(q.id)
            correct = is_correct(submitted, q.correct_answer)
            if correct:
                raw += 1
            per_question.append(
                PerQuestionResult(
                    question_id=q.id,
                    type=q.type,
                    correct=correct,
                    submitted=submitted,
                    correct_answer=q.correct_answer,
                    explanation=q.explanation,
                )
            )
        return raw, per_question

    @classmethod
    async def submit(
        cls, session: AsyncSession, user: User, payload: ReadingSubmitRequest
    ) -> ReadingResultResponse:
        passage = await session.get(Passage, payload.passage_id)
        if passage is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Passage not found"
            )
        questions = await cls._questions(session, passage.id)
        total = len(questions)
        raw, per_question = await cls._grade(questions, payload.answers)
        band = reading_band(raw, total, passage.exam_type)

        attempt = ReadingAttempt(
            user_id=user.id,
            passage_id=passage.id,
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
            await WeaknessService.record(session, user.id, "reading", wrong_tags)
        await session.flush()
        return ReadingResultResponse(
            attempt_id=attempt.id,
            passage_id=passage.id,
            raw_score=raw,
            total_questions=total,
            band=band,
            per_question=per_question,
        )

    @classmethod
    async def get_attempt(
        cls, session: AsyncSession, user: User, attempt_id: str
    ) -> ReadingResultResponse:
        attempt = await session.get(ReadingAttempt, attempt_id)
        if attempt is None or attempt.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found"
            )
        questions = await cls._questions(session, attempt.passage_id)
        _, per_question = await cls._grade(questions, attempt.answers)
        return ReadingResultResponse(
            attempt_id=attempt.id,
            passage_id=attempt.passage_id,
            raw_score=attempt.raw_score,
            total_questions=attempt.total_questions,
            band=attempt.band,
            per_question=per_question,
        )
