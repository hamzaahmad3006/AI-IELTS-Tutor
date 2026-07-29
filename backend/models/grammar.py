"""Grammar lesson ORM model.

`weakness_tags` links a lesson to the tags the AI records on scored attempts,
so the app can recommend exactly what a learner is getting wrong.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class GrammarLesson(Base, TimestampMixin):
    __tablename__ = "grammar_lessons"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    concept_tag: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[Any] = mapped_column(JSON, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="intermediate", nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    # Weakness tags this lesson addresses (matches models.weakness.Weakness.tag).
    weakness_tags: Mapped[Any] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)
