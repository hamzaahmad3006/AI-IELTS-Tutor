"""Vocabulary ORM models: the shared word bank and per-learner SRS review state."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VocabItem(Base, TimestampMixin):
    """A word in the shared vocabulary bank."""

    __tablename__ = "vocab_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    word: Mapped[str] = mapped_column(String(80), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    lexical_field: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)
    cefr_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)


class VocabReview(Base, TimestampMixin):
    """Per-learner spaced-repetition state for a vocabulary item (SM-2 style)."""

    __tablename__ = "vocab_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_vocab_review_user_item"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    item_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("vocab_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # SM-2 scheduling state.
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True, nullable=False
    )
    last_grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
