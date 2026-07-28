"""Vocabulary controller: SRS review queue, grading, and progress stats.

Words are prioritised by the learner's weak lexical fields where possible, so
vocabulary practice reinforces what the AI has actually flagged.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from pydantic import Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.srs import DEFAULT_EASE, ScheduleState, next_state
from models.user import User
from models.vocabulary import VocabItem, VocabReview

from .base import CamelModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# ---------- Schemas ----------
class VocabCard(CamelModel):
    item_id: str
    word: str
    definition: str
    example: str | None
    lexical_field: str | None
    cefr_level: str | None
    is_new: bool


class VocabQueue(CamelModel):
    items: list[VocabCard]
    due_count: int
    new_count: int


class GradeRequest(CamelModel):
    item_id: str
    grade: int = Field(ge=0, le=5)


class GradeResponse(CamelModel):
    item_id: str
    repetitions: int
    interval_days: int
    ease_factor: float
    due_at: datetime
    total_reviews: int


class VocabStats(CamelModel):
    total_items: int
    started: int
    due_now: int
    mastered: int


# ---------- Seeding (dev/demo content) ----------
_SEED_WORDS: list[dict[str, str]] = [
    {
        "word": "detrimental",
        "definition": "Tending to cause harm or damage.",
        "example": "Excessive screen time can be detrimental to sleep quality.",
        "lexical_field": "environment",
        "cefr_level": "C1",
    },
    {
        "word": "mitigate",
        "definition": "To make something bad less severe or serious.",
        "example": "Planting trees helps mitigate the effects of urban heat.",
        "lexical_field": "environment",
        "cefr_level": "C1",
    },
    {
        "word": "prevalent",
        "definition": "Widespread in a particular area or at a particular time.",
        "example": "Remote work has become prevalent in many industries.",
        "lexical_field": "society",
        "cefr_level": "B2",
    },
    {
        "word": "compelling",
        "definition": "Evoking interest or conviction in a powerful way.",
        "example": "She made a compelling argument for later school start times.",
        "lexical_field": "argument",
        "cefr_level": "B2",
    },
    {
        "word": "substantial",
        "definition": "Of considerable importance, size, or worth.",
        "example": "There has been a substantial increase in cycling.",
        "lexical_field": "data",
        "cefr_level": "B2",
    },
    {
        "word": "underpin",
        "definition": "To support, justify, or form the basis for something.",
        "example": "These findings underpin the government's new policy.",
        "lexical_field": "argument",
        "cefr_level": "C1",
    },
    {
        "word": "disparity",
        "definition": "A great difference between things.",
        "example": "The report highlights the disparity in exam results.",
        "lexical_field": "society",
        "cefr_level": "C1",
    },
    {
        "word": "fluctuate",
        "definition": "To rise and fall irregularly in number or amount.",
        "example": "Sales fluctuated sharply over the three-year period.",
        "lexical_field": "data",
        "cefr_level": "B2",
    },
]


async def _ensure_seeded(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(VocabItem))
    if count and count > 0:
        return
    for row in _SEED_WORDS:
        session.add(VocabItem(**row, source="seed"))
    await session.flush()


class VocabularyController:
    @staticmethod
    async def get_queue(
        session: AsyncSession, user: User, limit: int = 10
    ) -> VocabQueue:
        """Return due reviews first, then unseen words to fill the session."""
        await _ensure_seeded(session)
        now = _utcnow()

        due_rows = list(
            await session.scalars(
                select(VocabReview)
                .where(VocabReview.user_id == user.id, VocabReview.due_at <= now)
                .order_by(VocabReview.due_at)
                .limit(limit)
            )
        )
        due_ids = [row.item_id for row in due_rows]

        cards: list[VocabCard] = []
        if due_ids:
            items = {
                item.id: item
                for item in await session.scalars(
                    select(VocabItem).where(VocabItem.id.in_(due_ids))
                )
            }
            for review in due_rows:
                item = items.get(review.item_id)
                if item is not None:
                    cards.append(_to_card(item, is_new=False))

        # Fill the remainder with words the learner has never seen.
        remaining = limit - len(cards)
        if remaining > 0:
            seen = list(
                await session.scalars(
                    select(VocabReview.item_id).where(VocabReview.user_id == user.id)
                )
            )
            query = select(VocabItem)
            if seen:
                query = query.where(VocabItem.id.not_in(seen))
            new_items = list(await session.scalars(query.limit(remaining)))
            cards.extend(_to_card(item, is_new=True) for item in new_items)

        new_count = sum(1 for card in cards if card.is_new)
        return VocabQueue(
            items=cards,
            due_count=len(cards) - new_count,
            new_count=new_count,
        )

    @staticmethod
    async def grade(
        session: AsyncSession, user: User, payload: GradeRequest
    ) -> GradeResponse:
        item = await session.get(VocabItem, payload.item_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found"
            )

        review = await session.scalar(
            select(VocabReview).where(
                VocabReview.user_id == user.id,
                VocabReview.item_id == payload.item_id,
            )
        )
        if review is None:
            # Column defaults are applied at INSERT, so set the starting SRS
            # state explicitly - it is read below before the row is flushed.
            review = VocabReview(
                user_id=user.id,
                item_id=payload.item_id,
                repetitions=0,
                interval_days=0,
                ease_factor=DEFAULT_EASE,
                due_at=_utcnow(),
                total_reviews=0,
            )
            session.add(review)

        updated = next_state(
            ScheduleState(
                repetitions=review.repetitions,
                interval_days=review.interval_days,
                ease_factor=review.ease_factor,
            ),
            payload.grade,
        )
        review.repetitions = updated.repetitions
        review.interval_days = updated.interval_days
        review.ease_factor = updated.ease_factor
        review.due_at = _utcnow() + timedelta(days=updated.interval_days)
        review.last_grade = payload.grade
        review.total_reviews += 1
        await session.flush()

        return GradeResponse(
            item_id=review.item_id,
            repetitions=review.repetitions,
            interval_days=review.interval_days,
            ease_factor=review.ease_factor,
            due_at=_aware(review.due_at),
            total_reviews=review.total_reviews,
        )

    @staticmethod
    async def stats(session: AsyncSession, user: User) -> VocabStats:
        await _ensure_seeded(session)
        now = _utcnow()
        total = int(
            await session.scalar(select(func.count()).select_from(VocabItem)) or 0
        )
        started = int(
            await session.scalar(
                select(func.count())
                .select_from(VocabReview)
                .where(VocabReview.user_id == user.id)
            )
            or 0
        )
        due_now = int(
            await session.scalar(
                select(func.count())
                .select_from(VocabReview)
                .where(VocabReview.user_id == user.id, VocabReview.due_at <= now)
            )
            or 0
        )
        # "Mastered" = recalled successfully enough times to be on a long interval.
        mastered = int(
            await session.scalar(
                select(func.count())
                .select_from(VocabReview)
                .where(
                    VocabReview.user_id == user.id,
                    VocabReview.repetitions >= 3,
                )
            )
            or 0
        )
        return VocabStats(
            total_items=total, started=started, due_now=due_now, mastered=mastered
        )


def _to_card(item: VocabItem, *, is_new: bool) -> VocabCard:
    return VocabCard(
        item_id=item.id,
        word=item.word,
        definition=item.definition,
        example=item.example,
        lexical_field=item.lexical_field,
        cefr_level=item.cefr_level,
        is_new=is_new,
    )
