"""Learner profile ORM model (onboarding output)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class LearnerProfile(Base, TimestampMixin):
    __tablename__ = "learner_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    exam_type: Mapped[str] = mapped_column(String(20), default="academic", nullable=False)
    self_level: Mapped[str] = mapped_column(String(20), default="beginner", nullable=False)
    cefr_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_band: Mapped[float] = mapped_column(Float, nullable=False)
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    baseline_speaking: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_writing: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_reading: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_listening: Mapped[float | None] = mapped_column(Float, nullable=True)

    consent_voice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
