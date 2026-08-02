"""Speaking Part 1 and Part 3 question bank.

Separate from `cue_cards`, which models Part 2 specifically: a cue card is one
prompt with bullet points and its own prep/speak allowances, whereas Parts 1 and
3 are ordered sets of short questions on a theme. Forcing both into one table
would leave half the columns null in every row.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class SpeakingQuestion(Base, TimestampMixin):
    __tablename__ = "speaking_questions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    #: 1 = familiar personal topics, 3 = abstract discussion. Part 2 lives in
    #: `cue_cards`.
    part: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    difficulty: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), default="seed", nullable=False)
