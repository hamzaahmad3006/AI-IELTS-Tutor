"""Smoke test for the Listening module (clip delivery + auto-grading + band)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_listening.db")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Listener",
                "email": "listener@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "listener@example.com", "password": "StrongPass123"},
        ).json()
        headers = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        # Fetch a clip (auto-seeds). Answers/transcript not exposed on questions.
        r = client.get("/v1/listening/clips", headers=headers)
        assert r.status_code == 200, r.text
        clip = r.json()
        assert clip["audioUrl"].endswith(".mp3")
        assert len(clip["questions"]) == 3
        for q in clip["questions"]:
            assert "correctAnswer" not in q
        qids = [q["id"] for q in clip["questions"]]

        # All correct
        answers = {
            qids[0]: "student card",
            qids[1]: "Second floor of the science building",
            qids[2]: "ten",
        }
        r = client.post(
            "/v1/listening/attempts",
            headers=headers,
            json={"audioId": clip["id"], "answers": answers},
        )
        assert r.status_code == 201, r.text
        result = r.json()
        assert result["rawScore"] == 3
        assert result["band"] == 9.0, result
        assert result["perQuestion"][0]["answerTimestamp"] is not None
        attempt_id = result["attemptId"]

        # Partially correct
        r2 = client.post(
            "/v1/listening/attempts",
            headers=headers,
            json={
                "audioId": clip["id"],
                "answers": {qids[0]: "id card", qids[1]: clip["questions"][1]["options"][1], qids[2]: "nine"},
            },
        )
        assert r2.status_code == 201, r2.text
        assert r2.json()["rawScore"] == 1

        # Fetch back
        r = client.get(f"/v1/listening/attempts/{attempt_id}", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["band"] == 9.0

    print("LISTENING SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
