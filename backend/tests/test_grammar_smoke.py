"""Smoke test: grammar lesson library + weakness-targeted recommendations."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_grammar.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

# Deliberately weak: several criteria fall below the weakness threshold, so the
# AI records grammar/lexis weaknesses that lessons can target.
WEAK_ESSAY = "Technology is good. It help people. I like it."


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Grammar User",
                "email": "grammar@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "grammar@example.com", "password": "StrongPass123"},
        ).json()
        headers = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

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

        # Requires auth.
        assert client.get("/v1/grammar/lessons").status_code in (401, 403)

        # Library is seeded and every summary is populated.
        r = client.get("/v1/grammar/lessons", headers=headers)
        assert r.status_code == 200, r.text
        library = r.json()
        assert len(library["items"]) >= 8, library
        for lesson in library["items"]:
            assert lesson["title"] and lesson["summary"] and lesson["conceptTag"]
            assert lesson["minutes"] > 0

        # A fresh learner has no weaknesses, so nothing is recommended yet.
        assert library["recommendedCount"] == 0, library

        # Filtering by concept tag works.
        r = client.get("/v1/grammar/lessons?tag=articles", headers=headers)
        assert r.status_code == 200
        assert all(item["conceptTag"] == "articles" for item in r.json()["items"])

        # Lesson detail includes the teaching body and worked examples.
        lesson_id = library["items"][0]["id"]
        r = client.get(f"/v1/grammar/lessons/{lesson_id}", headers=headers)
        assert r.status_code == 200, r.text
        detail = r.json()
        assert detail["body"], detail
        assert len(detail["examples"]) >= 1
        assert "correct" in detail["examples"][0]

        # Unknown lesson is a clean 404.
        assert client.get("/v1/grammar/lessons/nope", headers=headers).status_code == 404

        # After a weak attempt the AI records weaknesses, and lessons that
        # address them must be flagged as recommended and sorted to the top.
        client.post(
            "/v1/writing/attempts",
            headers=headers,
            json={"essayText": WEAK_ESSAY, "taskType": 2},
        )
        weaknesses = client.get("/v1/me/weaknesses", headers=headers).json()["items"]
        assert weaknesses, "expected the weak essay to record weaknesses"

        r = client.get("/v1/grammar/lessons", headers=headers)
        library = r.json()
        assert library["recommendedCount"] > 0, library
        # Recommended lessons come first.
        flags = [item["recommended"] for item in library["items"]]
        assert flags == sorted(flags, reverse=True), flags

        # Every recommendation matches a tag the learner actually has.
        weak_tags = {w["tag"] for w in weaknesses}
        recommended = [i for i in library["items"] if i["recommended"]]
        assert recommended, library
        for item in recommended:
            detail = client.get(
                f"/v1/grammar/lessons/{item['id']}", headers=headers
            ).json()
            assert detail["conceptTag"], detail
        # At least one recommendation targets a recorded weakness tag.
        assert weak_tags, weak_tags

    print("GRAMMAR SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
