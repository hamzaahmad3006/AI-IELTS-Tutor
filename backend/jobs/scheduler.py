"""Periodic maintenance jobs.

Two things need to happen on a schedule and neither was happening: the retention
sweep, and weakness decay. Both were written, documented as daily jobs, and then
never run by anything -- so severities never decayed and nothing was ever swept.

Deliberately a scheduler and not a queue. Celery or arq solve "this request
needs work done later", and this app has none of that: every AI call is
synchronous request-and-response. What it actually has is "run this once a day",
and adding Redis plus a broker plus a worker process to answer that would be
infrastructure with no user.

Multi-instance safety comes from the database. A job is claimed with a
conditional UPDATE that only matches when the recorded start is older than the
interval, so two instances racing produce one winner and one no-op. That is the
same guarantee a distributed lock would give, using a table that already exists.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.job_run import JobRun

logger = logging.getLogger("jobs")

JobFn = Callable[[AsyncSession], Awaitable[str]]

#: How often the loop wakes to see whether anything is due. Well under the
#: shortest interval, so a job runs close to when it should without the loop
#: itself being busy.
TICK_SECONDS = 60

#: Truncated before storage: this column is for an operator glancing at why a
#: job failed, not for a stack trace.
MAX_DETAIL = 500


@dataclass(frozen=True)
class PeriodicJob:
    name: str
    interval: timedelta
    run: JobFn
    #: One line on what it does, for the admin view.
    description: str = ""


async def _ensure_row(session: AsyncSession, name: str) -> None:
    """Create the bookkeeping row if this job has never run.

    A race here is harmless and expected: two instances starting together both
    try to insert, one gets an IntegrityError, and both proceed with a row that
    exists. Catching it beats locking for something this cheap.
    """
    existing = await session.scalar(select(JobRun).where(JobRun.name == name))
    if existing is not None:
        return
    session.add(JobRun(name=name))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()


async def claim(
    session: AsyncSession, job: PeriodicJob, *, now: datetime | None = None
) -> bool:
    """Try to take ownership of this job's next run.

    True means this process should run it. The claim is a single conditional
    UPDATE, so it is atomic against every other instance without a lock service.

    The start time is written at claim time rather than at completion, so a job
    that takes an hour is not claimed again half way through.
    """
    now = now or datetime.now(tz=timezone.utc)
    cutoff = now - job.interval

    result = await session.execute(
        update(JobRun)
        .where(
            JobRun.name == job.name,
            # `is_(None)` covers the first ever run, where there is nothing to
            # compare against.
            (JobRun.last_started_at.is_(None)) | (JobRun.last_started_at < cutoff),
        )
        .values(last_started_at=now)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return (result.rowcount or 0) > 0


async def record(
    session: AsyncSession,
    job: PeriodicJob,
    *,
    status: str,
    detail: str,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(tz=timezone.utc)
    row = await session.scalar(select(JobRun).where(JobRun.name == job.name))
    if row is None:
        return
    row.last_finished_at = now
    row.last_status = status
    row.last_detail = detail[:MAX_DETAIL]
    # Reset on success, increment on failure: a job that has failed forty times
    # in a row is a different situation from one that failed once, and the
    # count is what tells them apart without trawling logs.
    row.consecutive_failures = 0 if status == "ok" else row.consecutive_failures + 1
    await session.commit()


async def run_due_jobs(
    session_factory: Callable[[], AsyncSession],
    jobs: list[PeriodicJob],
    *,
    now: datetime | None = None,
) -> list[str]:
    """Run whatever is due. Returns the names of the jobs that ran.

    A failure is recorded and the loop continues to the next job. One broken
    job must not stop the others: retention failing should not also mean
    weaknesses stop decaying.
    """
    ran: list[str] = []

    for job in jobs:
        async with session_factory() as session:
            await _ensure_row(session, job.name)
            if not await claim(session, job, now=now):
                continue

        ran.append(job.name)
        try:
            async with session_factory() as session:
                detail = await job.run(session)
            status = "ok"
        except Exception as exc:  # noqa: BLE001 - one job, not the scheduler
            status, detail = "failed", f"{type(exc).__name__}: {exc}"
            logger.exception("job failed", extra={"job": job.name})

        # A separate session, because the one the job used may be poisoned by
        # whatever raised -- and losing the record of a failure is how a job
        # silently stops working.
        async with session_factory() as session:
            await record(session, job, status=status, detail=detail, now=now)

        logger.info(
            "job finished",
            extra={"job": job.name, "status": status, "detail": detail[:200]},
        )

    return ran


async def scheduler_loop(
    session_factory: Callable[[], AsyncSession],
    jobs: list[PeriodicJob],
    *,
    tick_seconds: int = TICK_SECONDS,
    stop: asyncio.Event | None = None,
) -> None:
    """Wake periodically and run whatever is due, until stopped."""
    stop = stop or asyncio.Event()
    while not stop.is_set():
        try:
            await run_due_jobs(session_factory, jobs)
        except Exception:  # noqa: BLE001 - the loop must outlive any failure
            logger.exception("scheduler tick failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=tick_seconds)
        except asyncio.TimeoutError:
            continue
