"""Smoke test for the auth flow against a temporary SQLite database.

Run:  python -m pytest tests/test_auth_smoke.py   (or execute directly)
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_smoke.db")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def run() -> None:
    with TestClient(app) as client:
        # Register
        r = client.post(
            "/v1/auth/register",
            json={
                "fullName": "Sarah Ahmed",
                "email": "sarah@example.com",
                "password": "StrongPass123",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["user"]["email"] == "sarah@example.com"
        assert body["tokens"]["accessToken"]
        access = body["tokens"]["accessToken"]
        refresh = body["tokens"]["refreshToken"]

        # /me with access token
        r = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert r.status_code == 200, r.text
        assert r.json()["fullName"] == "Sarah Ahmed"

        # Login
        r = client.post(
            "/v1/auth/login",
            json={"email": "sarah@example.com", "password": "StrongPass123"},
        )
        assert r.status_code == 200, r.text

        # Wrong password rejected
        r = client.post(
            "/v1/auth/login",
            json={"email": "sarah@example.com", "password": "wrong"},
        )
        assert r.status_code == 401, r.text

        # --- Onboarding + profile ---
        auth_h = {"Authorization": f"Bearer {access}"}

        # No profile yet -> 404
        r = client.get("/v1/profile", headers=auth_h)
        assert r.status_code == 404, r.text

        # Submit onboarding
        r = client.post(
            "/v1/onboarding",
            headers=auth_h,
            json={
                "examType": "academic",
                "selfLevel": "intermediate",
                "targetBand": 7.0,
                "examDate": "2026-10-15",
                "dailyMinutes": 60,
                "consentVoice": True,
                "consentAi": True,
            },
        )
        assert r.status_code == 201, r.text
        prof = r.json()
        assert prof["targetBand"] == 7.0
        assert prof["baselines"]["speaking"] is None

        # Get profile
        r = client.get("/v1/profile", headers=auth_h)
        assert r.status_code == 200, r.text
        assert r.json()["dailyMinutes"] == 60

        # Patch profile (partial)
        r = client.patch("/v1/profile", headers=auth_h, json={"targetBand": 7.5})
        assert r.status_code == 200, r.text
        assert r.json()["targetBand"] == 7.5
        assert r.json()["examType"] == "academic"  # unchanged

        # --- Refresh rotation (moved last) ---
        r = client.post("/v1/auth/refresh", json={"refreshToken": refresh})
        assert r.status_code == 200, r.text
        r = client.post("/v1/auth/refresh", json={"refreshToken": refresh})
        assert r.status_code == 401, r.text

    print("AUTH + PROFILE SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
