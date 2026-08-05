"""Interview session ORM model (a speaking test in progress).

The script and the turns are stored as JSON rather than normalised into their
own tables. A session is written once and then appended to a handful of times,
is only ever read whole, and never queried across -- nobody asks "which
candidates were asked about teachers". Normalising it would buy joins nobody
performs at the cost of a schema that has to change whenever the exam shape
does.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


#: JSONB on Postgres, plain JSON on SQLite so the test suites still run.
_JSON = JSON().with_variant(JSONB(), "postgresql")


class InterviewSession(Base, TimestampMixin):
    __tablename__ = "interview_sessions"

    # One learner's sessions, newest first -- the only way this is ever listed.
    __table_args__ = (
        Index("ix_interview_sessions_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    #: Mirrors core.interview.Phase.
    phase: Mapped[str] = mapped_column(String(24), default="greeting", nullable=False)

    #: The questions this exam will ask, fixed at creation. Frozen rather than
    #: re-drawn per turn so a resumed session continues the same test instead of
    #: quietly becoming a different one.
    script: Mapped[Any] = mapped_column(_JSON, nullable=False)

    #: Every turn, in order, as {speaker, text, phase}.
    turns: Mapped[Any] = mapped_column(_JSON, default=list, nullable=False)

    #: Position within the current part.
    cursor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    #: How the transcript was produced, so a bad score can be traced to a bad
    #: transcription rather than assumed to be the model's fault.
    transcript_source: Mapped[str] = mapped_column(
        String(30), default="unknown", nullable=False
    )

    #: Set when the session is scored. The attempt holds the bands; this is
    #: only the link, so scoring logic stays in one place.
    speaking_attempt_id: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
