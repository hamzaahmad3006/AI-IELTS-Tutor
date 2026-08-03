"""Full mock test ORM model.

Stores only the assembled content ids and the resulting bands. The individual
answers are not duplicated here: each section is submitted through its own module
controller, which creates a real attempt row, so a mock test contributes to
history, trends and weakness tracking exactly like ordinary practice.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class MockTest(Base, TimestampMixin):
    __tablename__ = "mock_tests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), default="in_progress", nullable=False
    )

    #: Content assembled at start, so a resumed test serves the same items.
    passage_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    clip_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    writing_prompt_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cue_card_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    reading_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    listening_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    writing_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    speaking_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_band: Mapped[float | None] = mapped_column(Float, nullable=True)

    #: Readiness verdict as rendered at completion, so reopening an old result
    #: shows what the learner was actually told at the time.
    readiness: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
