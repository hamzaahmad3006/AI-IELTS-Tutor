"""Liveness, readiness and metrics endpoints.

Kept unauthenticated and outside the /v1 prefix: an orchestrator probes these
before the application is known to work, and a probe that needs a working login
cannot report that login is broken.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.health import readiness
from core.metrics import render
from db.session import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: is this process able to answer at all?

    Checks nothing external, on purpose. A liveness failure means "restart me",
    and restarting every pod because the database blipped turns a recoverable
    outage into a crash loop. Dependencies belong in /ready.
    """
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: DbSession, response: Response) -> dict[str, object]:
    """Readiness: can this process serve a request right now?

    Returns 503 when a critical dependency is unreachable, so the orchestrator
    stops sending traffic while leaving the process alive to recover.
    """
    report = await readiness(session)
    if not report.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report.to_dict()


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus exposition. Excluded from the OpenAPI schema: it is for the
    scraper, and its format is not this API's contract."""
    return render()
