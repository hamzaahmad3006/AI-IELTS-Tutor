"""Cue card ORM model (Speaking Part 2 question bank)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class CueCard(Base, TimestampMixin):
    __tablename__ = "cue_cards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    topic: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    bullet_points: Mapped[Any] = mapped_column(JSON, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    prep_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    speak_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)
