"""Smoke test for the Listening module (clip delivery + auto-grading + band)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_listening.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

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
        # Clips are served at random, so expected answers are derived from the
        # grading response rather than hard-coded for one clip.
        r = client.get("/v1/listening/clips", headers=headers)
        assert r.status_code == 200, r.text
        clip = r.json()
        # Served from the media route; format is an implementation detail.
        assert clip["audioUrl"].startswith("/media/"), clip["audioUrl"]
        total = len(clip["questions"])
        assert total > 0
        for q in clip["questions"]:
            assert "correctAnswer" not in q

        # First attempt: deliberately wrong -> reveals the answer key.
        wrong = {q["id"]: "__definitely_wrong__" for q in clip["questions"]}
        r = client.post(
            "/v1/listening/attempts",
            headers=headers,
            json={"audioId": clip["id"], "answers": wrong},
        )
        assert r.status_code == 201, r.text
        wrong_result = r.json()
        assert wrong_result["rawScore"] == 0, wrong_result
        assert wrong_result["totalQuestions"] == total
        assert wrong_result["perQuestion"][0]["answerTimestamp"] is not None

        # Second attempt: use the revealed key -> full marks, band 9.0.
        correct = {
            pq["questionId"]: pq["correctAnswer"]
            for pq in wrong_result["perQuestion"]
        }
        r = client.post(
            "/v1/listening/attempts",
            headers=headers,
            json={"audioId": clip["id"], "answers": correct},
        )
        assert r.status_code == 201, r.text
        result = r.json()
        assert result["rawScore"] == total, result
        assert result["band"] == 9.0, result
        attempt_id = result["attemptId"]

        # Fetch back
        r = client.get(f"/v1/listening/attempts/{attempt_id}", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["band"] == 9.0

    print("LISTENING SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
