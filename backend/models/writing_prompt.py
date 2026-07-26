"""Writing prompt ORM model (Task 1 / Task 2 question bank)."""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class WritingPrompt(Base, TimestampMixin):
    __tablename__ = "writing_prompts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    exam_type: Mapped[str] = mapped_column(String(20), default="academic", nullable=False)
    task_number: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(120), nullable=True)
    asset_ref: Mapped[str | None] = mapped_column(String(300), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    min_words: Mapped[int] = mapped_column(Integer, default=250, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)
