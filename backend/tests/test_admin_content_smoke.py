"""Smoke test: admin content CRUD for passages + questions."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_admin_content.db")

from fastapi.testclient import TestClient  # noqa: E402

from core.config import get_settings  # noqa: E402
from main import app  # noqa: E402


def run() -> None:
    settings = get_settings()
    with TestClient(app) as client:
        # Learner (forbidden)
        client.post(
            "/v1/auth/register",
            json={"fullName": "Learner Two", "email": "learner2@example.com", "password": "StrongPass123"},
        )
        learner = client.post(
            "/v1/auth/login",
            json={"email": "learner2@example.com", "password": "StrongPass123"},
        ).json()
        lh = {"Authorization": f"Bearer {learner['tokens']['accessToken']}"}
        assert client.get("/v1/admin/passages", headers=lh).status_code == 403
        assert (
            client.post("/v1/admin/passages", headers=lh, json={"title": "x", "body": "y"}).status_code
            == 403
        )

        # Admin
        admin = client.post(
            "/v1/auth/login",
            json={"email": settings.seed_admin_email, "password": settings.seed_admin_password},
        ).json()
        ah = {"Authorization": f"Bearer {admin['tokens']['accessToken']}"}

        # Create a passage with two questions
        r = client.post(
            "/v1/admin/passages",
            headers=ah,
            json={
                "title": "Renewable Energy",
                "body": "Solar and wind power are increasingly important sources of clean energy.",
                "examType": "academic",
                "difficulty": "hard",
                "topic": "environment",
                "questions": [
                    {
                        "type": "mcq",
                        "prompt": "Which are named as clean energy sources?",
                        "options": ["Coal", "Solar and wind", "Oil", "Gas"],
                        "correctAnswer": "Solar and wind",
                        "explanation": "The passage names solar and wind.",
                    },
                    {
                        "type": "true_false_notgiven",
                        "prompt": "Clean energy is decreasing in importance.",
                        "options": ["true", "false", "not_given"],
                        "correctAnswer": "false",
                    },
                ],
            },
        )
        assert r.status_code == 201, r.text
        passage = r.json()
        pid = passage["id"]
        assert len(passage["questions"]) == 2
        assert passage["questions"][0]["correctAnswer"] == "Solar and wind"  # admin sees answers

        # Invalid question type -> 422
        r = client.post(
            f"/v1/admin/passages/{pid}/questions",
            headers=ah,
            json={"type": "bogus", "prompt": "?", "correctAnswer": "x"},
        )
        assert r.status_code == 422, r.text

        # List includes it
        assert any(p["id"] == pid for p in client.get("/v1/admin/passages", headers=ah).json()["items"])

        # Update passage
        r = client.patch(f"/v1/admin/passages/{pid}", headers=ah, json={"difficulty": "medium"})
        assert r.status_code == 200 and r.json()["difficulty"] == "medium"

        # Add a question -> 3 total
        r = client.post(
            f"/v1/admin/passages/{pid}/questions",
            headers=ah,
            json={"type": "short_answer", "prompt": "Name one clean source.", "correctAnswer": "solar"},
        )
        assert r.status_code == 201, r.text
        qid = r.json()["id"]
        assert len(client.get(f"/v1/admin/passages/{pid}", headers=ah).json()["questions"]) == 3

        # Update + delete the question -> back to 2
        assert client.patch(f"/v1/admin/questions/{qid}", headers=ah, json={"prompt": "Updated?"}).status_code == 200
        assert client.delete(f"/v1/admin/questions/{qid}", headers=ah).status_code == 204
        assert len(client.get(f"/v1/admin/passages/{pid}", headers=ah).json()["questions"]) == 2

        # A learner can fetch this admin-created passage via the public endpoint (no answers)
        pub = client.get("/v1/reading/passages", headers=lh)
        assert pub.status_code == 200
        for q in pub.json()["questions"]:
            assert "correctAnswer" not in q

        # Delete the passage -> gone
        assert client.delete(f"/v1/admin/passages/{pid}", headers=ah).status_code == 204
        assert client.get(f"/v1/admin/passages/{pid}", headers=ah).status_code == 404

    print("ADMIN CONTENT SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
