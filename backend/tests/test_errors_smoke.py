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
        # Specific rather than a blanket code: a client can branch on
        # "already_exists" without string-matching the title.
        _assert_problem(r.json(), 409, "already_exists")

        # Missing bearer token on a protected route -> problem
        r = client.get("/v1/analytics/overview", headers=h)
        assert r.status_code in (401, 403), r.text
        # Bare HTTPExceptions still get a code derived from the status, so
        # nothing falls back to an opaque "http_error".
        _assert_problem(
            r.json(),
            r.status_code,
            "unauthenticated" if r.status_code == 401 else "forbidden",
        )

        # Correlation id is generated when the client does not send one
        r = client.post("/v1/auth/register", json={"fullName": "X", "email": "bad", "password": "short"})
        assert r.status_code == 422
        assert r.headers.get("X-Correlation-Id")  # server-generated
        assert r.json()["correlationId"]

        # `h` above carries only a correlation id, so an authenticated call
        # needs a real token.
        login = client.post(
            "/v1/auth/login",
            json={"email": "real@example.com", "password": "StrongPass123"},
        ).json()
        # Correlation id included too: _assert_problem checks it echoes back.
        auth = {
            "Authorization": f"Bearer {login['tokens']['accessToken']}",
            "X-Correlation-Id": CID,
        }

        # An unknown id is a plain 404 with a specific code. It is also what a
        # row owned by somebody else returns, so an id cannot be probed for
        # existence.
        missing = client.get("/v1/writing/attempts/does-not-exist", headers=auth)
        assert missing.status_code == 404, missing.text
        _assert_problem(missing.json(), 404, "not_found")

        # Every problem carries a resolvable type URI, never "about:blank",
        # which by itself tells a client nothing.
        for body in (
            client.post(
                "/v1/auth/login",
                json={"email": "nobody@example.com", "password": "StrongPass123"},
            ).json(),
            missing.json(),
        ):
            assert body["type"].startswith("https://errors.aitutor.app/"), body
            assert body["code"] and body["code"] != "http_error", body

    print("ERRORS/VALIDATION SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
