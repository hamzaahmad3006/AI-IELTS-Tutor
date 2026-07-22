"""Content ORM models: reading passages and their questions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class Passage(Base, TimestampMixin):
    __tablename__ = "passages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    exam_type: Mapped[str] = mapped_column(String(20), default="academic", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    topic: Mapped[str | None] = mapped_column(String(120), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    passage_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("passages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[Any] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
