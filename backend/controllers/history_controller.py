"""Attempt history: paginated lists of a learner's past attempts per module."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from models.attempt import WritingAttempt
from models.listening import ListeningAttempt
from models.reading import ReadingAttempt
from models.speaking import SpeakingAttempt
from models.user import User

from .base import CamelModel
from .pagination import paginate


# ---------- Item DTOs ----------
class WritingHistoryItem(CamelModel):
    attempt_id: str
    task_type: int
    word_count: int
    overall_band: float | None
    status: str
    created_at: datetime


class SpeakingHistoryItem(CamelModel):
    attempt_id: str
    part: int | None
    overall_band: float | None
    status: str
    created_at: datetime


class ReadingHistoryItem(CamelModel):
    attempt_id: str
    passage_id: str | None
    raw_score: int
    total_questions: int
    band: float
    created_at: datetime


class ListeningHistoryItem(CamelModel):
    attempt_id: str
    audio_id: str | None
    raw_score: int
    total_questions: int
    band: float
    created_at: datetime


# ---------- Page DTOs ----------
class WritingHistoryPage(CamelModel):
    items: list[WritingHistoryItem]
    next_cursor: str | None


class SpeakingHistoryPage(CamelModel):
    items: list[SpeakingHistoryItem]
    next_cursor: str | None


class ReadingHistoryPage(CamelModel):
    items: list[ReadingHistoryItem]
    next_cursor: str | None


class ListeningHistoryPage(CamelModel):
    items: list[ListeningHistoryItem]
    next_cursor: str | None


class HistoryController:
    @staticmethod
    async def writing(
        session: AsyncSession, user: User, cursor: str | None, limit: int
    ) -> WritingHistoryPage:
        rows, next_cursor = await paginate(
            session, WritingAttempt, [WritingAttempt.user_id == user.id], cursor, limit
        )
        return WritingHistoryPage(
            items=[
                WritingHistoryItem(
                    attempt_id=r.id,
                    task_type=r.task_type,
                    word_count=r.word_count,
                    overall_band=r.overall_band,
                    status=r.status,
                    created_at=r.created_at,
                )
                for r in rows
            ],
            next_cursor=next_cursor,
        )

    @staticmethod
    async def speaking(
        session: AsyncSession, user: User, cursor: str | None, limit: int
    ) -> SpeakingHistoryPage:
        rows, next_cursor = await paginate(
            session, SpeakingAttempt, [SpeakingAttempt.user_id == user.id], cursor, limit
        )
        return SpeakingHistoryPage(
            items=[
                SpeakingHistoryItem(
                    attempt_id=r.id,
                    part=r.part,
                    overall_band=r.overall_band,
                    status=r.status,
                    created_at=r.created_at,
                )
                for r in rows
            ],
            next_cursor=next_cursor,
        )

    @staticmethod
    async def reading(
        session: AsyncSession, user: User, cursor: str | None, limit: int
    ) -> ReadingHistoryPage:
        rows, next_cursor = await paginate(
            session, ReadingAttempt, [ReadingAttempt.user_id == user.id], cursor, limit
        )
        return ReadingHistoryPage(
            items=[
                ReadingHistoryItem(
                    attempt_id=r.id,
                    passage_id=r.passage_id,
                    raw_score=r.raw_score,
                    total_questions=r.total_questions,
                    band=r.band,
                    created_at=r.created_at,
                )
                for r in rows
            ],
            next_cursor=next_cursor,
        )

    @staticmethod
    async def listening(
        session: AsyncSession, user: User, cursor: str | None, limit: int
    ) -> ListeningHistoryPage:
        rows, next_cursor = await paginate(
            session, ListeningAttempt, [ListeningAttempt.user_id == user.id], cursor, limit
        )
        return ListeningHistoryPage(
            items=[
                ListeningHistoryItem(
                    attempt_id=r.id,
                    audio_id=r.audio_id,
                    raw_score=r.raw_score,
                    total_questions=r.total_questions,
                    band=r.band,
                    created_at=r.created_at,
                )
                for r in rows
            ],
            next_cursor=next_cursor,
        )
