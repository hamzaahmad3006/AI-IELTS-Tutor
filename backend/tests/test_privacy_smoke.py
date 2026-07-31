"""Smoke test: data export and irreversible account deletion."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_privacy.db")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

PASSWORD = "StrongPass123"


def _reading_attempt(client: TestClient, headers: dict[str, str]) -> None:
    """Give the account some content so the export has something to hold."""
    passage = client.get("/v1/reading/passages", headers=headers).json()
    answers = {q["id"]: "__wrong__" for q in passage["questions"]}
    client.post(
        "/v1/reading/attempts",
        headers=headers,
        json={"passageId": passage["id"], "answers": answers},
    )


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Priya Sharma",
                "email": "privacy@example.com",
                "password": PASSWORD,
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "privacy@example.com", "password": PASSWORD},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        # Both endpoints require auth.
        assert client.get("/v1/me/export").status_code in (401, 403)
        assert client.delete("/v1/me").status_code in (401, 403)

        client.post(
            "/v1/onboarding",
            headers=h,
            json={
                "examType": "academic",
                "selfLevel": "intermediate",
                "targetBand": 7.0,
                "examDate": "2026-12-01",
                "dailyMinutes": 30,
                "consentVoice": False,
                "consentAi": True,
            },
        )
        _reading_attempt(client, h)

        # ---- Export ----
        r = client.get("/v1/me/export", headers=h)
        assert r.status_code == 200, r.text
        export = r.json()

        assert export["account"]["email"] == "privacy@example.com"
        assert export["account"]["fullName"] == "Priya Sharma"
        assert export["exportedAt"]
        # Credentials must never leave the server, even to their owner.
        assert "passwordHash" not in export["account"]
        assert "password_hash" not in export["account"]

        assert export["profile"] is not None, export
        assert export["profile"]["target_band"] == 7.0
        assert len(export["readingAttempts"]) == 1, export["readingAttempts"]
        # Every owned table is represented, even when empty.
        for key in (
            "writingAttempts",
            "speakingAttempts",
            "listeningAttempts",
            "weaknesses",
            "vocabReviews",
        ):
            assert key in export, key

        # ---- Delete ----
        r = client.delete("/v1/me", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["deleted"] is True
        assert body["removed"]["account"] == 1
        assert body["removed"]["readingAttempts"] == 1
        assert body["removed"]["profile"] == 1
        # Sessions die with the account.
        assert body["removed"]["refreshTokens"] >= 1

        # The token is now worthless and the credentials no longer work.
        assert client.get("/v1/me/export", headers=h).status_code in (401, 403)
        relogin = client.post(
            "/v1/auth/login",
            json={"email": "privacy@example.com", "password": PASSWORD},
        )
        assert relogin.status_code == 401, relogin.text

        # The address is free again — deletion, not a soft-disable.
        again = client.post(
            "/v1/auth/register",
            json={
                "fullName": "Someone Else",
                "email": "privacy@example.com",
                "password": PASSWORD,
            },
        )
        assert again.status_code == 201, again.text

    print("PRIVACY SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
