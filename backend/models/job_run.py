"""Bookkeeping for periodic jobs.

One row per job, holding when it last started. That row is also the lock: a job
is claimed with a conditional UPDATE that only matches when the recorded start
is older than the interval, so two instances racing produce one winner and one
no-op without any coordination service.

This is why there is no Redis here. The lock a scheduler needs is "did anyone
run this in the last day", and the database already answers that atomically.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class JobRun(Base):
    __tablename__ = "job_runs"

    #: The job's name is the primary key: there is exactly one row per job, and
    #: a surrogate id would allow two.
    name: Mapped[str] = mapped_column(String(60), primary_key=True)

    #: When the current or most recent run was claimed. The lock compares
    #: against this, so it is set at claim time rather than at completion --
    #: otherwise a long run would be claimed again while still going.
    last_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    #: "ok" or "failed". A job that has never finished has neither.
    last_status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    #: What it did, or why it failed. Read by an operator wondering whether
    #: retention has actually been running.
    last_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Consecutive failures. A job failing every hour for a week is a different
    #: situation from one that failed once, and the count is what distinguishes
    #: them without trawling logs.
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
