"""Plan usage, as the learner sees it."""

from __future__ import annotations

from .base import CamelModel


class PlanUsageOut(CamelModel):
    plan: str
    label: str
    #: AI-scored attempts used this calendar month.
    used: int
    #: None means unlimited. Reported as null rather than as a large number so
    #: a client can render "unlimited" instead of "9999 remaining".
    limit: int | None
    remaining: int | None
    spoken_interview: bool
