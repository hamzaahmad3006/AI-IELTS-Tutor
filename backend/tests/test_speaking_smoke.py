"""Smoke test for the Speaking AI-scoring vertical (offline mock provider)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_speaking.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

TRANSCRIPT = (
    "Well, last month I travelled to the scenic coastal town of Amalfi in Italy. "
    "It was an absolutely breathtaking experience. The cliffs were steep and the "
    "water was a deep, crystal-clear blue. I particularly enjoyed the local "
    "cuisine, especially the fresh seafood which was caught daily by the local "
    "fishermen. The atmosphere was vibrant yet peaceful, and I would love to "
    "return there someday to explore the surrounding villages."
)


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Speaker",
                "email": "speaker@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "speaker@example.com", "password": "StrongPass123"},
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

        r = client.post(
            "/v1/speaking/attempts",
            headers=headers,
            json={"transcript": TRANSCRIPT, "part": 2, "durationSec": 95},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "scored", body
        assert body["part"] == 2
        crit = body["criteria"]
        assert crit is not None
        for key in (
            "fluencyCoherence",
            "lexicalResource",
            "grammaticalRange",
            "pronunciation",
        ):
            assert 0 <= crit[key] <= 9 and (crit[key] * 2) % 1 == 0, crit
        band = body["overallBand"]
        assert 0 <= band <= 9 and (band * 2) % 1 == 0, band
        attempt_id = body["attemptId"]

        # Fetch back
        r = client.get(f"/v1/speaking/attempts/{attempt_id}", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["overallBand"] == band

        # Cross-user isolation
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Other",
                "email": "other-spk@example.com",
                "password": "StrongPass123",
            },
        )
        other = client.post(
            "/v1/auth/login",
            json={"email": "other-spk@example.com", "password": "StrongPass123"},
        ).json()
        r = client.get(
            f"/v1/speaking/attempts/{attempt_id}",
            headers={"Authorization": f"Bearer {other['tokens']['accessToken']}"},
        )
        assert r.status_code == 404, r.text

    print("SPEAKING SCORING SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
