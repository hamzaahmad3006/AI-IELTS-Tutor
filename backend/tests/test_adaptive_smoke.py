"""Smoke test: adaptive difficulty resolution + recommendations from weaknesses."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_adaptive.db")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

WEAK_ESSAY = "Technology is good. It helps people. I like it very much every day."


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={"fullName": "Adapt Learner", "email": "adapt@example.com", "password": "StrongPass123"},
        )
        h = {
            "Authorization": "Bearer "
            + client.post(
                "/v1/auth/login",
                json={"email": "adapt@example.com", "password": "StrongPass123"},
            ).json()["tokens"]["accessToken"]
        }

        # No history -> every module resolves to medium
        r = client.get("/v1/me/adaptive-difficulty", headers=h)
        assert r.status_code == 200, r.text
        by_module = {m["module"]: m for m in r.json()["modules"]}
        assert len(by_module) == 4
        for m in by_module.values():
            assert m["difficulty"] in ("easy", "medium", "hard")
            assert m["difficulty"] == "medium"  # cold start
            assert m["recentBand"] is None

        # No weaknesses yet -> empty recommendations with a helpful message
        r = client.get("/v1/me/recommendations", headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["items"] == []
        assert r.json()["message"]

        # Create weak attempts -> weaknesses -> recommendations appear
        client.post("/v1/writing/attempts", headers=h, json={"essayText": WEAK_ESSAY, "taskType": 2})
        client.post("/v1/speaking/attempts", headers=h, json={"transcript": "Um, I think, uh, yes.", "part": 1})

        r = client.get("/v1/me/recommendations", headers=h)
        assert r.status_code == 200, r.text
        recs = r.json()["items"]
        assert len(recs) > 0, recs
        for rec in recs:
            assert rec["title"] and rec["action"]
            assert rec["difficulty"] in ("easy", "medium", "hard")
            assert rec["module"] in ("writing", "speaking", "reading", "listening")
        # Ordered by weakness priority (severity desc after equal recency)
        sev = [rec["severity"] for rec in recs]
        assert sev == sorted(sev, reverse=True)

        # Writing now has history -> difficulty resolves from the recent (low) band
        r = client.get("/v1/me/adaptive-difficulty", headers=h)
        writing = {m["module"]: m for m in r.json()["modules"]}["writing"]
        assert writing["recentBand"] is not None
        assert writing["difficulty"] in ("easy", "medium")  # low band -> not hard

        # Reading still serves a passage under adaptive resolution
        assert client.get("/v1/reading/passages", headers=h).status_code == 200

    print("ADAPTIVE SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
