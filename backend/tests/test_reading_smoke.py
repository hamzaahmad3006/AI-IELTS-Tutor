"""Smoke test for the Reading module (passage delivery + auto-grading + band)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_reading.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Reader",
                "email": "reader@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "reader@example.com", "password": "StrongPass123"},
        ).json()
        headers = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        # Fetch a passage (auto-seeds on first call). Answers not exposed.
        # Passages are served at random, so the test derives expected answers
        # from the grading response rather than hard-coding one passage.
        r = client.get("/v1/reading/passages", headers=headers)
        assert r.status_code == 200, r.text
        passage = r.json()
        total = len(passage["questions"])
        assert total > 0
        for q in passage["questions"]:
            assert "correctAnswer" not in q  # answers must not leak

        # First attempt: deliberately wrong answers -> reveals the answer key.
        wrong = {q["id"]: "__definitely_wrong__" for q in passage["questions"]}
        r = client.post(
            "/v1/reading/attempts",
            headers=headers,
            json={"passageId": passage["id"], "answers": wrong},
        )
        assert r.status_code == 201, r.text
        wrong_result = r.json()
        assert wrong_result["rawScore"] == 0, wrong_result
        assert wrong_result["totalQuestions"] == total
        assert not any(pq["correct"] for pq in wrong_result["perQuestion"])

        # Second attempt: use the revealed key -> full marks, band 9.0.
        correct = {
            pq["questionId"]: pq["correctAnswer"]
            for pq in wrong_result["perQuestion"]
        }
        r = client.post(
            "/v1/reading/attempts",
            headers=headers,
            json={"passageId": passage["id"], "answers": correct},
        )
        assert r.status_code == 201, r.text
        result = r.json()
        assert result["rawScore"] == total, result
        assert result["band"] == 9.0, result  # all correct -> band 9
        assert all(pq["correct"] for pq in result["perQuestion"])
        attempt_id = result["attemptId"]

        # Fetch the scored attempt back
        r = client.get(f"/v1/reading/attempts/{attempt_id}", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["band"] == 9.0

    print("READING SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
