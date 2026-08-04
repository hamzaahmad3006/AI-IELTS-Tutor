"""Speaking attempt ORM model (transcript + AI score)."""

from __future__ import annotations

from typing import Any

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class SpeakingAttempt(Base, TimestampMixin):
    __tablename__ = "speaking_attempts"

    # Serves "this user's rows, in time order" without a sort step.
    __table_args__ = (
        Index("ix_speaking_attempts_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    part: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="scored", nullable=False)

    overall_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    fluency_coherence: Mapped[float | None] = mapped_column(Float, nullable=True)
    lexical_resource: Mapped[float | None] = mapped_column(Float, nullable=True)
    grammatical_range: Mapped[float | None] = mapped_column(Float, nullable=True)
    pronunciation: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Resolved highlight spans: [{start, end, quote, tag, note}].
    issues: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    ai_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
