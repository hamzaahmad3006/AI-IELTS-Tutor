"""Smoke test for the Writing AI-scoring vertical (uses the offline mock
provider, so no Groq key is required)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_writing.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

ESSAY = (
    "Nowadays, technology has become increasingly important in our daily lives. "
    "Some people argue that it complicates our routines, while others believe it "
    "simplifies them. In my opinion, although technology introduces new challenges, "
    "its benefits clearly outweigh the drawbacks. For instance, communication is "
    "now instantaneous, and access to information has never been easier. "
    "Furthermore, automation has freed people from repetitive tasks, allowing them "
    "to focus on creative work. Consequently, I firmly believe that technology, "
    "when used responsibly, enriches modern life rather than diminishing it."
)


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Test Writer",
                "email": "writer@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "writer@example.com", "password": "StrongPass123"},
        ).json()
        headers = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        # Onboarding, because consent is now enforced: an account that never
        # answered the consent question has not agreed to AI scoring, and
        # treating "never asked" as "agreed" is what made the checkbox
        # decorative in the first place.
        client.post(
            "/v1/onboarding",
            headers=headers,
            json={
                "examType": "academic",
                "selfLevel": "intermediate",
                "targetBand": 7.0,
                "examDate": None,
                "dailyMinutes": 30,
                "consentVoice": True,
                "consentAi": True,
            },
        )

        # Submit essay for scoring
        r = client.post(
            "/v1/writing/attempts",
            headers=headers,
            json={"essayText": ESSAY, "taskType": 2},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "scored", body
        assert body["criteria"] is not None
        band = body["overallBand"]
        assert 0 <= band <= 9 and (band * 2) % 1 == 0, f"invalid band {band}"
        assert body["wordCount"] > 0
        attempt_id = body["attemptId"]

        # Fetch it back
        r = client.get(f"/v1/writing/attempts/{attempt_id}", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["overallBand"] == band

        # Another user cannot read it
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Other",
                "email": "other@example.com",
                "password": "StrongPass123",
            },
        )
        other = client.post(
            "/v1/auth/login",
            json={"email": "other@example.com", "password": "StrongPass123"},
        ).json()
        r = client.get(
            f"/v1/writing/attempts/{attempt_id}",
            headers={"Authorization": f"Bearer {other['tokens']['accessToken']}"},
        )
        assert r.status_code == 404, r.text

    print("WRITING SCORING SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
