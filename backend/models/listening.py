"""Listening attempt ORM model."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class ListeningAttempt(Base, TimestampMixin):
    __tablename__ = "listening_attempts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    audio_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("audio_clips.id", ondelete="SET NULL"), nullable=True
    )
    answers: Mapped[Any] = mapped_column(JSON, nullable=False)
    raw_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    band: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
