"""Smoke test: input validation + RFC 7807 problem+json error contract."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_errors.db")
# This suite exercises validation, not rate limiting (it registers repeatedly).
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

CID = "corr-test-abc123"


def _assert_problem(body: dict, status: int, code: str) -> None:
    assert body["status"] == status, body
    assert body["code"] == code, body
    assert "title" in body and "type" in body
    assert body["correlationId"] == CID, body


def run() -> None:
    with TestClient(app) as client:
        h = {"X-Correlation-Id": CID}

        # Malformed email -> 422 validation problem
        r = client.post(
            "/v1/auth/register",
            headers=h,
            json={"fullName": "Valid Name", "email": "not-an-email", "password": "StrongPass123"},
        )
        assert r.status_code == 422, r.text
        assert r.headers.get("X-Correlation-Id") == CID
        body = r.json()
        _assert_problem(body, 422, "validation")
        assert any(e["field"].endswith("email") for e in body["errors"]), body

        # Weak password (no digit / too short) -> 422
        r = client.post(
            "/v1/auth/register",
            headers=h,
            json={"fullName": "Valid Name", "email": "ok@example.com", "password": "short"},
        )
        assert r.status_code == 422, r.text
        assert any(e["field"].endswith("password") for e in r.json()["errors"])

        # Too-short name -> 422
        r = client.post(
            "/v1/auth/register",
            headers=h,
            json={"fullName": "A", "email": "ok2@example.com", "password": "StrongPass123"},
        )
        assert r.status_code == 422, r.text

        # Valid registration succeeds
        r = client.post(
            "/v1/auth/register",
            headers=h,
            json={"fullName": "Real User", "email": "real@example.com", "password": "StrongPass123"},
        )
        assert r.status_code == 201, r.text

        # Duplicate email -> 409 problem
        r = client.post(
            "/v1/auth/register",
            headers=h,
            json={"fullName": "Real User", "email": "real@example.com", "password": "StrongPass123"},
        )
        assert r.status_code == 409, r.text
        _assert_problem(r.json(), 409, "http_error")

        # Missing bearer token on a protected route -> problem
        r = client.get("/v1/analytics/overview", headers=h)
        assert r.status_code in (401, 403), r.text
        _assert_problem(r.json(), r.status_code, "http_error")

        # Correlation id is generated when the client does not send one
        r = client.post("/v1/auth/register", json={"fullName": "X", "email": "bad", "password": "short"})
        assert r.status_code == 422
        assert r.headers.get("X-Correlation-Id")  # server-generated
        assert r.json()["correlationId"]

    print("ERRORS/VALIDATION SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
