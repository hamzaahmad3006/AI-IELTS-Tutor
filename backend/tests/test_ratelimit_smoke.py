"""Smoke test: rate limiting returns 429 problem+json with Retry-After."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_ratelimit.db")
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

    print("RATE LIMIT SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
