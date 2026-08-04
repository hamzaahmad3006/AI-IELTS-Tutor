"""AI interaction ORM model: one row per AI/scoring call for cost & monitoring."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class AIInteraction(Base, TimestampMixin):
    __tablename__ = "ai_interactions"

    # Serves "this user's rows, in time order" without a sort step.
    __table_args__ = (
        Index("ix_ai_interactions_user_created", "user_id", "created_at"),
        Index("ix_ai_interactions_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    feature: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ok", nullable=False)
    #: Which prompt produced this call. Null for rows written before the
    #: registry existed - those genuinely have no known version.
    prompt_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
