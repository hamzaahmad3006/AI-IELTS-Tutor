"""Smoke test: rate limiting returns 429 problem+json with Retry-After."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_ratelimit.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)
# Enable limiting with a low login limit so the breach is quick to trigger.
os.environ["RATE_LIMIT_ENABLED"] = "true"
os.environ["RATE_LIMIT_LOGIN_PER_MIN"] = "3"

from fastapi.testclient import TestClient  # noqa: E402

from core.config import get_settings  # noqa: E402
from main import app  # noqa: E402


def run() -> None:
    limit = get_settings().rate_limit_login_per_min
    assert limit == 3, "test expects a login limit of 3"

    creds = {"email": "nobody@example.com", "password": "StrongPass123"}
    with TestClient(app) as client:
        # First `limit` attempts pass the limiter (invalid creds -> 401)
        for _ in range(limit):
            r = client.post("/v1/auth/login", json=creds)
            assert r.status_code == 401, r.text

        # The next one is blocked by the limiter -> 429 problem+json
        r = client.post("/v1/auth/login", json=creds)
        assert r.status_code == 429, r.text
        assert r.headers.get("Retry-After") is not None
        assert r.headers.get("X-RateLimit-Limit") == str(limit)
        body = r.json()
        assert body["code"] == "rate_limited", body
        assert body["status"] == 429
        assert "correlationId" in body

        # Correct credentials do not buy a way past the limiter. If they did,
        # the limit would only slow down people who type accurately -- which is
        # the opposite of what a brute-force defence is for, since the attacker
        # stops exactly when they start typing accurately.
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Rate Limited",
                "email": "ratelimited@example.com",
                "password": "StrongPass123",
            },
        )
        r = client.post(
            "/v1/auth/login",
            json={"email": "ratelimited@example.com", "password": "StrongPass123"},
        )
        assert r.status_code == 429, r.status_code

        # The limiter is scoped, not global: exhausting login must not take the
        # rest of the API down with it. A defence that becomes a self-inflicted
        # outage gets switched off in production.
        assert client.get("/health").status_code == 200

    print("RATE LIMIT SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
