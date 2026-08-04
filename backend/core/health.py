"""Dependency checks behind /health and /ready.

The two probes answer different questions and must not be confused:

* **Liveness** (/health) asks "is this process wedged?" A failure means kill and
  restart me. It deliberately checks nothing external. If liveness checked the
  database, a database blip would restart every pod at once, turning a
  recoverable outage into a crash loop that also destroys the in-flight
  requests that were about to succeed.
* **Readiness** (/ready) asks "can I serve a request right now?" A failure means
  take me out of the load balancer and leave me running. That is where
  dependency checks belong, because the correct response to an unreachable
  database is to stop being sent traffic, not to die.

The previous /ready returned "ready" unconditionally with a TODO, which meant an
orchestrator would route traffic to a process whose database was gone and every
request would 500.

No check here calls a paid API. A readiness probe runs every few seconds
forever; a probe that made a real AI call would bill for uptime. The provider
check therefore verifies configuration, and says exactly that.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings

#: A probe that hangs is worse than one that fails: the orchestrator waits, the
#: request piles up behind it, and nothing is learned.
CHECK_TIMEOUT_S = 5.0


class Status(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class CheckResult:
    name: str
    status: Status
    #: One line a human on call can act on. Never a raw stack trace.
    detail: str
    duration_ms: float
    #: False for checks that should not keep traffic away on their own.
    critical: bool = True

    @property
    def blocks_traffic(self) -> bool:
        return self.critical and self.status is Status.FAILED


async def check_database(session: AsyncSession) -> CheckResult:
    """Round-trip a trivial query. Proves the pool, the network and the DB."""
    started = time.perf_counter()
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), CHECK_TIMEOUT_S)
    except asyncio.TimeoutError:
        return CheckResult(
            name="database",
            status=Status.FAILED,
            detail=f"No response within {CHECK_TIMEOUT_S:.0f}s",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
    except Exception as exc:  # noqa: BLE001 - any failure means not ready
        # Type only, never the message: connection errors routinely contain the
        # host, the user and sometimes the password, and this endpoint is
        # usually reachable from inside the cluster without authentication.
        return CheckResult(
            name="database",
            status=Status.FAILED,
            detail=f"Query failed ({type(exc).__name__})",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    elapsed = (time.perf_counter() - started) * 1000
    return CheckResult(
        name="database",
        status=Status.OK,
        detail="Reachable",
        duration_ms=round(elapsed, 2),
    )


def check_ai_provider() -> CheckResult:
    """Confirm the provider is *configured*. Deliberately makes no call.

    A live call here would be billed on every probe, forever, which is a large
    bill for information that changes rarely. Misconfiguration is the failure
    this can actually catch, and it is the common one.
    """
    started = time.perf_counter()
    settings = get_settings()
    provider = settings.ai_provider

    if provider == "mock":
        status, detail = Status.DEGRADED, "Mock provider: scores are not real"
    elif getattr(settings, "groq_api_key", None):
        status, detail = Status.OK, f"{provider} configured (not called)"
    else:
        status, detail = Status.FAILED, f"{provider} selected but no API key set"

    return CheckResult(
        name="ai_provider",
        status=status,
        detail=detail,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        # Scoring is one feature; reading, listening and history all work
        # without it. Pulling the whole process out of the load balancer for a
        # provider outage would take down more than the outage did.
        critical=False,
    )


@dataclass
class ReadinessReport:
    ready: bool
    checks: list[CheckResult]

    @property
    def status(self) -> Status:
        if any(c.blocks_traffic for c in self.checks):
            return Status.FAILED
        if any(c.status is not Status.OK for c in self.checks):
            return Status.DEGRADED
        return Status.OK

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "ready": self.ready,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "detail": c.detail,
                    "durationMs": c.duration_ms,
                    "critical": c.critical,
                }
                for c in self.checks
            ],
        }


async def readiness(session: AsyncSession) -> ReadinessReport:
    """Run every dependency check and decide whether to accept traffic."""
    checks = [await check_database(session), check_ai_provider()]
    return ReadinessReport(
        ready=not any(c.blocks_traffic for c in checks), checks=checks
    )
