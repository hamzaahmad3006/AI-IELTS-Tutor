"""Smoke test: the periodic job scheduler.

The lock is the part that has to be right. Two API instances both running the
retention sweep is not a crash -- it is a second delete pass over rows the first
one already took, and nothing in the logs says it happened twice.

The other assertions are about a job failing without taking anything else with
it: retention breaking must not also stop weaknesses decaying.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_scheduler.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from sqlalchemy import select  # noqa: E402

from db.base import Base  # noqa: E402
from db.session import SessionLocal, engine  # noqa: E402
from jobs.definitions import JOBS  # noqa: E402
from jobs.scheduler import (  # noqa: E402
    PeriodicJob,
    _ensure_row,
    claim,
    record,
    run_due_jobs,
)
from models.job_run import JobRun  # noqa: E402

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)


async def _reset() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def _job(name: str, run, hours: int = 24) -> PeriodicJob:
    return PeriodicJob(name=name, interval=timedelta(hours=hours), run=run)


async def check_claim_is_exclusive() -> None:
    """Two instances racing produce one winner.

    Without this, every API instance runs the retention sweep -- a second
    delete pass over rows the first already took, with nothing in the logs to
    say it happened twice.
    """
    await _reset()
    job = _job("exclusive", lambda s: asyncio.sleep(0))

    async with SessionLocal() as session:
        await _ensure_row(session, job.name)

    async def attempt() -> bool:
        async with SessionLocal() as session:
            return await claim(session, job, now=NOW)

    results = [await attempt() for _ in range(5)]
    assert results.count(True) == 1, results

    # ...and still only one after the interval has partly elapsed.
    async with SessionLocal() as session:
        assert not await claim(session, job, now=NOW + timedelta(hours=23))

    # Once the interval is up, it is claimable again.
    async with SessionLocal() as session:
        assert await claim(session, job, now=NOW + timedelta(hours=25))


async def check_first_run_is_claimable() -> None:
    """A job that has never run has nothing to compare against."""
    await _reset()
    job = _job("first", lambda s: asyncio.sleep(0))
    async with SessionLocal() as session:
        await _ensure_row(session, job.name)
        assert await claim(session, job, now=NOW)


async def check_claim_marks_start_not_finish() -> None:
    """A long job must not be claimed again while it is still running."""
    await _reset()
    job = _job("long", lambda s: asyncio.sleep(0))
    async with SessionLocal() as session:
        await _ensure_row(session, job.name)
        await claim(session, job, now=NOW)
        row = await session.scalar(select(JobRun).where(JobRun.name == job.name))
        assert row is not None and row.last_started_at is not None
        # Nothing has finished yet, which is the point: the lock is held from
        # the moment work begins.
        assert row.last_finished_at is None


async def check_failure_is_isolated_and_recorded() -> None:
    """One broken job must not stop the others."""
    await _reset()
    ran: list[str] = []

    async def ok(_session) -> str:
        ran.append("ok")
        return "did the thing"

    async def boom(_session) -> str:
        raise RuntimeError("upstream on fire")

    jobs = [_job("boom", boom), _job("ok", ok)]
    names = await run_due_jobs(SessionLocal, jobs, now=NOW)

    assert set(names) == {"boom", "ok"}
    assert ran == ["ok"], "a failing job stopped the next one"

    async with SessionLocal() as session:
        rows = {
            r.name: r for r in await session.scalars(select(JobRun))
        }
    assert rows["boom"].last_status == "failed"
    assert "RuntimeError" in (rows["boom"].last_detail or "")
    assert rows["boom"].consecutive_failures == 1
    assert rows["ok"].last_status == "ok"
    assert rows["ok"].last_detail == "did the thing"


async def check_failure_count_accumulates_and_resets() -> None:
    """Forty failures in a row is a different situation from one."""
    await _reset()
    failing = True

    async def flaky(_session) -> str:
        if failing:
            raise RuntimeError("still broken")
        return "recovered"

    job = _job("flaky", flaky, hours=1)

    for i in range(3):
        await run_due_jobs(SessionLocal, [job], now=NOW + timedelta(hours=i * 2))

    async with SessionLocal() as session:
        row = await session.scalar(select(JobRun).where(JobRun.name == "flaky"))
    assert row is not None and row.consecutive_failures == 3

    failing = False
    await run_due_jobs(SessionLocal, [job], now=NOW + timedelta(hours=10))
    async with SessionLocal() as session:
        row = await session.scalar(select(JobRun).where(JobRun.name == "flaky"))
    assert row is not None and row.consecutive_failures == 0
    assert row.last_status == "ok"


async def check_due_jobs_respect_the_interval() -> None:
    await _reset()
    calls: list[int] = []

    async def counting(_session) -> str:
        calls.append(1)
        return "ran"

    job = _job("counted", counting)

    await run_due_jobs(SessionLocal, [job], now=NOW)
    await run_due_jobs(SessionLocal, [job], now=NOW + timedelta(hours=1))
    await run_due_jobs(SessionLocal, [job], now=NOW + timedelta(hours=2))
    assert len(calls) == 1, "a daily job ran more than once in a day"

    await run_due_jobs(SessionLocal, [job], now=NOW + timedelta(days=1, hours=1))
    assert len(calls) == 2


async def check_detail_is_truncated() -> None:
    """The detail column is for a glance, not a stack trace."""
    await _reset()

    async def verbose(_session) -> str:
        return "x" * 5_000

    job = _job("verbose", verbose)
    await run_due_jobs(SessionLocal, [job], now=NOW)

    async with SessionLocal() as session:
        row = await session.scalar(select(JobRun).where(JobRun.name == "verbose"))
    assert row is not None and len(row.last_detail or "") <= 500


async def check_real_jobs_run() -> None:
    """The two jobs that exist actually execute against a real database."""
    await _reset()
    names = await run_due_jobs(SessionLocal, JOBS, now=NOW)
    assert set(names) == {"weakness_decay", "retention"}, names

    async with SessionLocal() as session:
        rows = {r.name: r for r in await session.scalars(select(JobRun))}
    for name in ("weakness_decay", "retention"):
        assert rows[name].last_status == "ok", rows[name].last_detail
        assert rows[name].last_detail

    # Retention runs for real, not as a dry run. A scheduled job that only ever
    # simulates lets data accumulate forever while reporting it is being swept.
    assert "deleted" in (rows["retention"].last_detail or "")


def run() -> None:
    asyncio.run(check_claim_is_exclusive())
    asyncio.run(check_first_run_is_claimable())
    asyncio.run(check_claim_marks_start_not_finish())
    asyncio.run(check_failure_is_isolated_and_recorded())
    asyncio.run(check_failure_count_accumulates_and_resets())
    asyncio.run(check_due_jobs_respect_the_interval())
    asyncio.run(check_detail_is_truncated())
    asyncio.run(check_real_jobs_run())

    print("SCHEDULER SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
