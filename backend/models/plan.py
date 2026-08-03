"""Study plan ORM models.

A plan is persisted rather than recomputed on every request so that completing a
task means something: progress has to survive a reload, and the learner must see
the same plan tomorrow that they saw today.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class StudyPlan(Base, TimestampMixin):
    __tablename__ = "study_plans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    target_band: Mapped[float] = mapped_column(Float, nullable=False)
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    weeks: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    #: Superseded plans are kept rather than deleted, so a learner can see that
    #: their plan changed and why.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PlanTask(Base, TimestampMixin):
    __tablename__ = "plan_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    week: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    module: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    #: Ordering weight; higher means it addresses a bigger gap.
    priority: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
