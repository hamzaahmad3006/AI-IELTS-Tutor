"""Writing controller: schemas + scoring business logic."""

from __future__ import annotations

import re

from fastapi import HTTPException, status
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.consent import require_consent
from ai.orchestrator import AIOrchestrator, ScoringError
from models.attempt import WritingAttempt
from models.user import User
from models.writing_prompt import WritingPrompt

from db.repository import OwnedRepository

from .ai_usage_controller import record_ai_interaction

from .base import CamelModel
from .weakness_controller import WeaknessService, criteria_below_threshold

#: Ownership-checked reads. Returns 404 rather than 403 for someone
#: else's row, so an id cannot be confirmed by a stranger.
_attempts = OwnedRepository(WritingAttempt, label="Attempt")


class WritingSubmitRequest(CamelModel):
    essay_text: str = Field(min_length=1, max_length=8000)
    task_type: int = Field(default=2, ge=1, le=2)
    prompt_text: str | None = None


class WritingPromptResponse(CamelModel):
    id: str
    exam_type: str
    task_number: int
    prompt: str
    topic: str | None
    asset_ref: str | None
    difficulty: str
    min_words: int


# ---------- Prompt bank seeding (dev/demo content) ----------
_SEED_PROMPTS: list[dict[str, object]] = [
    {
        "exam_type": "academic",
        "task_number": 2,
        "topic": "technology",
        "difficulty": "medium",
        "min_words": 250,
        "prompt": (
            "Some people believe technology has made our lives more complex, "
            "while others think it has simplified them. Discuss both views and "
            "give your own opinion."
        ),
    },
    {
        "exam_type": "academic",
        "task_number": 2,
        "topic": "education",
        "difficulty": "medium",
        "min_words": 250,
        "prompt": (
            "Some people think children should begin formal education as early as "
            "possible, while others believe they should start later. Discuss both "
            "views and give your own opinion."
        ),
    },
    {
        "exam_type": "academic",
        "task_number": 2,
        "topic": "environment",
        "difficulty": "hard",
        "min_words": 250,
        "prompt": (
            "Many governments prioritise economic growth over environmental "
            "protection. To what extent do you agree or disagree?"
        ),
    },
    {
        "exam_type": "general",
        "task_number": 1,
        "topic": "letter",
        "difficulty": "easy",
        "min_words": 150,
        "prompt": (
            "You recently stayed at a hotel and were unhappy with the service. "
            "Write a letter to the manager. In your letter: explain why you "
            "stayed there, describe the problems, and say what action you want."
        ),
    },
    {
        "exam_type": "academic",
        "task_number": 1,
        "topic": "chart",
        "difficulty": "medium",
        "min_words": 150,
        # The data is stated in the prompt rather than shown as a chart image,
        # so the task is fully answerable before Task 1 visual assets exist.
        "prompt": (
            "The table below shows the percentage of households owning selected "
            "devices in one country.\n\n"
            "Device         2005    2015    2025\n"
            "Desktop PC      61%     48%     22%\n"
            "Smartphone       9%     71%     94%\n"
            "Smart speaker    0%      4%     57%\n"
            "Tablet           0%     33%     41%\n\n"
            "Summarise the information by selecting and reporting the main "
            "features, and make comparisons where relevant."
        ),
    },
    {
        "exam_type": "academic",
        "task_number": 1,
        "topic": "process",
        "difficulty": "hard",
        "min_words": 150,
        "prompt": (
            "The stages below describe how glass bottles are recycled.\n\n"
            "1. Used bottles are collected from household bins.\n"
            "2. Bottles are sorted by colour and washed.\n"
            "3. Sorted glass is crushed into small pieces called cullet.\n"
            "4. Cullet is melted in a furnace at about 1500 degrees Celsius.\n"
            "5. Molten glass is poured into moulds to form new bottles.\n"
            "6. New bottles are cooled, inspected and shipped to bottlers.\n\n"
            "Summarise the information by selecting and reporting the main "
            "features of the process."
        ),
    },
    {
        "exam_type": "general",
        "task_number": 2,
        "topic": "work",
        "difficulty": "medium",
        "min_words": 250,
        "prompt": (
            "In many countries people are working longer hours than in the past. "
            "What are the causes of this, and what effects does it have on "
            "family life?"
        ),
    },
    {
        "exam_type": "general",
        "task_number": 1,
        "topic": "letter",
        "difficulty": "medium",
        "min_words": 150,
        "prompt": (
            "A friend is moving to your town and has asked for advice. Write a "
            "letter to your friend. In your letter: recommend an area to live "
            "in, explain how they can find work, and suggest one thing to do in "
            "their first week."
        ),
    },
]


async def _ensure_prompts_seeded(session: AsyncSession) -> None:
    """Seed any (exam_type, task_number) pairing that has no prompts yet.

    Checked per pairing rather than "is the table empty": an all-or-nothing
    guard means a database seeded from an earlier, smaller bank never receives
    newly added task types, and the learner silently gets the wrong paper.
    """
    existing = {
        (exam_type, task_number)
        for exam_type, task_number in (
            await session.execute(
                select(WritingPrompt.exam_type, WritingPrompt.task_number).distinct()
            )
        ).all()
    }
    added = False
    for row in _SEED_PROMPTS:
        if (row["exam_type"], row["task_number"]) in existing:
            continue
        session.add(WritingPrompt(**row, source="seed"))
        added = True
    if added:
        await session.flush()


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
    #: The learner's own text, so the client can diff it against the improved
    #: version rather than storing a second copy locally and drifting.
    essay_text: str
    prompt_text: str | None


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
        essay_text=attempt.essay_text,
        prompt_text=attempt.prompt_text,
    )


class WritingController:
    @staticmethod
    async def get_prompt(
        session: AsyncSession,
        exam_type: str,
        task_number: int,
        difficulty: str | None,
    ) -> WritingPromptResponse:
        await _ensure_prompts_seeded(session)
        query = select(WritingPrompt).where(
            WritingPrompt.exam_type == exam_type,
            WritingPrompt.task_number == task_number,
        )
        if difficulty and difficulty != "adaptive":
            query = query.where(WritingPrompt.difficulty == difficulty)
        # Random pick so repeated practice varies the prompt.
        prompt = await session.scalar(query.order_by(func.random()).limit(1))
        if prompt is None:
            # Relax the difficulty filter, but never the exam type: answering an
            # Academic Task 1 request with a General Training letter hands the
            # learner a different paper, assessed against different criteria.
            prompt = await session.scalar(
                select(WritingPrompt)
                .where(
                    WritingPrompt.exam_type == exam_type,
                    WritingPrompt.task_number == task_number,
                )
                .order_by(func.random())
                .limit(1)
            )
        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No prompt available"
            )
        return WritingPromptResponse(
            id=prompt.id,
            exam_type=prompt.exam_type,
            task_number=prompt.task_number,
            prompt=prompt.prompt,
            topic=prompt.topic,
            asset_ref=prompt.asset_ref,
            difficulty=prompt.difficulty,
            min_words=prompt.min_words,
        )

    @staticmethod
    async def submit(
        session: AsyncSession,
        user: User,
        orchestrator: AIOrchestrator,
        payload: WritingSubmitRequest,
    ) -> WritingResultResponse:
        # Checked before the attempt row is created: recording that a
        # learner submitted work we then refused to score would leave a
        # permanently unscored attempt in their history.
        await require_consent(session, user.id, "ai")

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
        await record_ai_interaction(
            session, user_id=user.id, feature="writing", usage=usage
        )
        weak_tags = criteria_below_threshold(
            {
                "task_response": score.task_response,
                "coherence_cohesion": score.coherence_cohesion,
                "lexical_resource": score.lexical_resource,
                "grammatical_range": score.grammatical_range,
            }
        )
        if weak_tags:
            await WeaknessService.record(session, user.id, "writing", weak_tags)
        await session.flush()
        return _to_response(attempt)

    @staticmethod
    async def get(
        session: AsyncSession, user: User, attempt_id: str
    ) -> WritingResultResponse:
        attempt = await _attempts.get_owned(session, attempt_id, user.id)
        return _to_response(attempt)
