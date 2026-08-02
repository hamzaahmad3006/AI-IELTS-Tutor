"""Part 1 and Part 3 question sets for the speaking module.

Part 1 asks short questions about familiar personal topics; Part 3 pushes the
same theme into abstract discussion. Both are served as an ordered set rather
than one question at a time, because an examiner works through a themed run and
scoring the run as a whole is what produces a meaningful band.
"""

from __future__ import annotations

import random

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.speaking_question import SpeakingQuestion

from .base import CamelModel

#: How many questions make up one themed run, per part.
QUESTIONS_PER_SET = {1: 4, 3: 3}


class SpeakingQuestionItem(CamelModel):
    id: str
    order_index: int
    question: str


class SpeakingQuestionSet(CamelModel):
    part: int
    topic: str
    difficulty: str
    questions: list[SpeakingQuestionItem]
    #: Guidance shown above the run, since the two parts are answered
    #: differently and a learner given no steer answers Part 3 like Part 1.
    guidance: str


_GUIDANCE = {
    1: (
        "Short, natural answers — two or three sentences each. Give a reason or "
        "an example rather than a bare yes or no."
    ),
    3: (
        "Longer, more analytical answers. Take a position, justify it, and "
        "consider the other side."
    ),
}

_SEED: list[dict[str, object]] = [
    # ---- Part 1: familiar, personal ----
    {"part": 1, "topic": "hometown", "difficulty": "easy", "questions": [
        "Where is your hometown, and what is it known for?",
        "What do you like most about living there?",
        "Has your hometown changed much since you were a child?",
        "Would you recommend it to a visitor? Why?",
    ]},
    {"part": 1, "topic": "work and study", "difficulty": "medium", "questions": [
        "Do you work, or are you a student?",
        "What made you choose that field?",
        "What is the most difficult part of it?",
        "What would you like to be doing in five years?",
    ]},
    {"part": 1, "topic": "free time", "difficulty": "easy", "questions": [
        "What do you usually do in your free time?",
        "Do you prefer spending free time alone or with other people?",
        "Have your hobbies changed over the last few years?",
        "Is it important to have time with no plans at all?",
    ]},
    # ---- Part 3: abstract, argued ----
    {"part": 3, "topic": "technology and society", "difficulty": "medium", "questions": [
        "How has technology changed the way people in your country communicate?",
        "Some people say constant connectivity harms relationships. Do you agree?",
        "What responsibility do technology companies have for how their products are used?",
    ]},
    {"part": 3, "topic": "education", "difficulty": "hard", "questions": [
        "Should governments fund university education for everyone? Why?",
        "How useful are examinations as a measure of ability?",
        "What skills will matter most to students entering work in twenty years?",
    ]},
    {"part": 3, "topic": "environment", "difficulty": "hard", "questions": [
        "Who should bear the cost of protecting the environment: individuals, companies or governments?",
        "Are people willing to change their habits for environmental reasons?",
        "Is economic growth compatible with environmental protection?",
    ]},
]


async def ensure_seeded(session: AsyncSession) -> None:
    """Seed any part that has no questions yet.

    Checked per part rather than "is the table empty", so a part added later
    still reaches a database seeded from an earlier bank.
    """
    existing = {
        part
        for (part,) in (
            await session.execute(select(SpeakingQuestion.part).distinct())
        ).all()
    }
    added = False
    for row in _SEED:
        part = int(row["part"])  # type: ignore[arg-type]
        if part in existing:
            continue
        topic = str(row["topic"])
        difficulty = str(row["difficulty"])
        for index, question in enumerate(row["questions"], start=1):  # type: ignore[arg-type]
            session.add(
                SpeakingQuestion(
                    part=part,
                    topic=topic,
                    question=str(question),
                    order_index=index,
                    difficulty=difficulty,
                    source="seed",
                )
            )
        added = True
    if added:
        await session.flush()


async def get_question_set(
    session: AsyncSession, part: int, difficulty: str | None
) -> SpeakingQuestionSet:
    if part not in QUESTIONS_PER_SET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only parts 1 and 3 have question sets; part 2 uses cue cards",
        )

    await ensure_seeded(session)

    topics_query = select(SpeakingQuestion.topic).where(
        SpeakingQuestion.part == part
    )
    if difficulty and difficulty != "adaptive":
        topics_query = topics_query.where(
            SpeakingQuestion.difficulty == difficulty
        )
    topics = [t for (t,) in (await session.execute(topics_query.distinct())).all()]

    if not topics:
        # Relax the difficulty filter, never the part: a Part 3 request answered
        # with Part 1 questions would be scored against the wrong expectations.
        topics = [
            t
            for (t,) in (
                await session.execute(
                    select(SpeakingQuestion.topic)
                    .where(SpeakingQuestion.part == part)
                    .distinct()
                )
            ).all()
        ]
    if not topics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No speaking questions available",
        )

    topic = random.choice(topics)
    rows = (
        await session.execute(
            select(SpeakingQuestion)
            .where(
                SpeakingQuestion.part == part,
                SpeakingQuestion.topic == topic,
            )
            .order_by(SpeakingQuestion.order_index)
            .limit(QUESTIONS_PER_SET[part])
        )
    ).scalars().all()

    return SpeakingQuestionSet(
        part=part,
        topic=topic,
        difficulty=rows[0].difficulty if rows else "medium",
        questions=[
            SpeakingQuestionItem(
                id=row.id, order_index=row.order_index, question=row.question
            )
            for row in rows
        ],
        guidance=_GUIDANCE[part],
    )


__all__ = [
    "SpeakingQuestionSet",
    "SpeakingQuestionItem",
    "ensure_seeded",
    "get_question_set",
    "QUESTIONS_PER_SET",
]
