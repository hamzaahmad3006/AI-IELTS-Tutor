"""Writing attempt ORM model (essay submission + AI score)."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class WritingAttempt(Base, TimestampMixin):
    __tablename__ = "writing_attempts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    task_type: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    essay_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="scored", nullable=False)

    overall_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    task_response: Mapped[float | None] = mapped_column(Float, nullable=True)
    coherence_cohesion: Mapped[float | None] = mapped_column(Float, nullable=True)
    lexical_resource: Mapped[float | None] = mapped_column(Float, nullable=True)
    grammatical_range: Mapped[float | None] = mapped_column(Float, nullable=True)

    feedback_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    improved_essay: Mapped[str | None] = mapped_column(Text, nullable=True)

    ai_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
