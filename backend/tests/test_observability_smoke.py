"""Smoke test: liveness, readiness and Prometheus metrics.

The assertions that matter here are the negative ones. A readiness probe that
always says ready is worse than none, because it silently converts an outage
into a stream of 500s; and a metrics endpoint is a place personal data leaks
into infrastructure that was never designed to hold it.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_observability.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from core.health import Status, check_ai_provider, check_database, readiness  # noqa: E402
from core.metrics import LATENCY_BUCKETS  # noqa: E402
from db.session import SessionLocal, get_db  # noqa: E402
from main import app  # noqa: E402

PASSWORD = "StrongPass123"


class BrokenSession:
    """A session whose every query fails, standing in for a lost database."""

    async def execute(self, *_args: object, **_kwargs: object) -> None:
        raise ConnectionRefusedError(
            "could not connect to server: postgres://admin:hunter2@db.internal:5432"
        )


class HangingSession:
    async def execute(self, *_args: object, **_kwargs: object) -> None:
        await asyncio.sleep(60)


async def check_dependency_checks() -> None:
    async with SessionLocal() as session:
        ok = await check_database(session)
        assert ok.status is Status.OK, ok
        assert ok.duration_ms >= 0

        report = await readiness(session)
        assert report.ready is True
        # Mock provider is configured but not real, so the overall verdict is
        # degraded rather than ok -- and still serving.
        assert report.status is Status.DEGRADED, report.to_dict()

    failed = await check_database(BrokenSession())  # type: ignore[arg-type]
    assert failed.status is Status.FAILED
    assert failed.blocks_traffic is True

    # The failure text must not carry the connection string. /ready is normally
    # reachable inside the cluster without authentication, and the exception
    # message here contains a host, a user and a password.
    assert "hunter2" not in failed.detail
    assert "db.internal" not in failed.detail
    assert "postgres://" not in failed.detail
    assert "ConnectionRefusedError" in failed.detail

    # A hung database fails the probe instead of hanging it. A probe that never
    # answers tells the orchestrator nothing while holding a worker.
    hung = await asyncio.wait_for(
        check_database(HangingSession()),  # type: ignore[arg-type]
        timeout=15,
    )
    assert hung.status is Status.FAILED
    assert "within" in hung.detail

    # An unreachable database makes the whole report unready.
    broken_report = await readiness(BrokenSession())  # type: ignore[arg-type]
    assert broken_report.ready is False
    assert broken_report.status is Status.FAILED

    # The provider check must never make a call: it is on a probe path that
    # runs every few seconds forever.
    provider = check_ai_provider()
    assert provider.critical is False, "an AI outage must not pull the pod from LB"
    assert provider.duration_ms < 50, "the provider check appears to do real I/O"


def check_probes(client: TestClient) -> None:
    live = client.get("/health")
    assert live.status_code == 200 and live.json()["status"] == "ok"

    r = client.get("/ready")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ready"] is True
    names = {c["name"] for c in body["checks"]}
    assert names == {"database", "ai_provider"}, names
    for c in body["checks"]:
        assert c["detail"] and "durationMs" in c

    # Both probes are usable before login: a probe that needs a working session
    # cannot report that sessions are broken.
    assert "Authorization" not in client.headers

    # The assertion this endpoint exists for. With the database unreachable,
    # /ready must return 503 so the orchestrator stops routing traffic here,
    # while /health keeps returning 200 so the process is not also killed.
    # The previous implementation returned "ready" unconditionally, which meant
    # a dead database produced a healthy-looking pod serving nothing but 500s.
    async def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    try:
        down = client.get("/ready")
        assert down.status_code == 503, down.text
        body = down.json()
        assert body["ready"] is False
        assert body["status"] == "failed"
        database = next(c for c in body["checks"] if c["name"] == "database")
        assert database["status"] == "failed"
        assert "hunter2" not in down.text and "db.internal" not in down.text

        assert client.get("/health").status_code == 200, "liveness must not follow"
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert client.get("/ready").status_code == 200, "override leaked"


def check_metrics(client: TestClient) -> None:
    # Generate traffic across a matched route, a 404 and an error path.
    client.post(
        "/v1/auth/register",
        json={"fullName": "Metrics User", "email": "metrics@example.com", "password": PASSWORD},
    )
    client.post(
        "/v1/auth/login", json={"email": "metrics@example.com", "password": PASSWORD}
    )
    client.get("/v1/writing/prompts")  # 401, still counted
    client.get("/definitely-not-a-route")
    client.get("/wp-admin/setup-config.php")

    r = client.get("/metrics")
    assert r.status_code == 200, r.text
    assert "text/plain" in r.headers["content-type"]
    body = r.text

    for metric in (
        "http_requests_total",
        "http_request_duration_seconds",
        "http_requests_in_progress",
    ):
        assert metric in body, metric

    # Route templates, not URLs: one series per route, not one per resource.
    assert 'route="/v1/auth/login"' in body

    # Unmatched paths collapse to a single series. Without this, anyone can grow
    # the metric store without limit just by requesting random URLs.
    assert 'route="<unmatched>"' in body
    assert "wp-admin" not in body
    assert "definitely-not-a-route" not in body

    # Status codes are recorded, including the failures.
    assert 'status="401"' in body or 'status="403"' in body
    assert 'status="404"' in body

    # No personal data. Metrics get scraped into infrastructure with much weaker
    # access control than the API, and are kept for months.
    for secret in ("metrics@example.com", PASSWORD, "Metrics User"):
        assert secret not in body, secret

    # The scrape does not count itself, or the number would climb on every
    # scrape regardless of whether anyone used the service.
    assert 'route="/metrics"' not in body

    # Histogram buckets are the configured ones, and cumulative: every bucket
    # count is at least the one below it, ending at +Inf.
    assert 'le="0.005"' in body and 'le="+Inf"' in body
    for edge in LATENCY_BUCKETS:
        assert f'le="{edge}"' in body, edge

    counts = [
        float(line.rsplit(" ", 1)[1])
        for line in body.splitlines()
        if line.startswith("http_request_duration_seconds_bucket")
        and 'route="/v1/auth/login"' in line
    ]
    assert counts, "no buckets recorded for the login route"
    assert counts == sorted(counts), counts
    assert counts[-1] > 0

    # The AI counters exist and moved: registering scores nothing, but the mock
    # provider is exercised by the login-adjacent flows in other suites. Assert
    # only that the series is declared, since this suite makes no scoring call.
    assert "ai_calls_total" in body or "ai_calls" in body


def run() -> None:
    asyncio.run(check_dependency_checks())
    with TestClient(app) as client:
        check_probes(client)
        check_metrics(client)

    print("OBSERVABILITY SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
