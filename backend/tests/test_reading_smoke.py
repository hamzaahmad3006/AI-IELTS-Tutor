"""Smoke test for the Reading module (passage delivery + auto-grading + band)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_reading.db")

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
        r = client.get("/v1/reading/passages", headers=headers)
        assert r.status_code == 200, r.text
        passage = r.json()
        assert len(passage["questions"]) == 3
        for q in passage["questions"]:
            assert "correctAnswer" not in q  # answers must not leak
        qids = [q["id"] for q in passage["questions"]]

        # Submit all-correct answers
        answers = {qids[0]: "China", qids[1]: "true", qids[2]: "black"}
        r = client.post(
            "/v1/reading/attempts",
            headers=headers,
            json={"passageId": passage["id"], "answers": answers},
        )
        assert r.status_code == 201, r.text
        result = r.json()
        assert result["rawScore"] == 3
        assert result["totalQuestions"] == 3
        assert result["band"] == 9.0, result  # 3/3 scaled to 40 -> band 9
        assert all(pq["correct"] for pq in result["perQuestion"])
        attempt_id = result["attemptId"]

        # Submit a partially-wrong set on a second attempt
        r2 = client.post(
            "/v1/reading/attempts",
            headers=headers,
            json={
                "passageId": passage["id"],
                "answers": {qids[0]: "India", qids[1]: "true", qids[2]: "green"},
            },
        )
        assert r2.status_code == 201, r2.text
        assert r2.json()["rawScore"] == 1

        # Fetch first attempt back
        r = client.get(f"/v1/reading/attempts/{attempt_id}", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["band"] == 9.0

    print("READING SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
