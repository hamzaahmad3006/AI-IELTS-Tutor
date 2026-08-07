"""Smoke test: adaptive difficulty resolution + recommendations from weaknesses."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_adaptive.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from core.adaptive import ema, level_for, resolve_level  # noqa: E402
from main import app  # noqa: E402

WEAK_ESSAY = "Technology is good. It helps people. I like it very much every day."


def check_scoring() -> None:
    """The level maths, tested directly rather than through four HTTP calls."""
    assert ema([]) is None  # no data is not a score
    assert ema([6.0]) == 6.0

    # Recency: four sessions, three weak and one strong. A flat mean gives 5.0
    # and keeps the learner on easy; the weighted average recognises the change.
    assert sum([4.0, 4.0, 4.0, 8.0]) / 4 == 5.0
    assert ema([4.0, 4.0, 4.0, 8.0]) > 5.5

    # ...and symmetrically, one bad session does not erase a good run.
    assert ema([7.5, 7.5, 7.5, 6.0]) > 6.5

    assert level_for(4.99) == "easy"
    assert level_for(5.0) == "medium"
    assert level_for(6.5) == "medium"
    assert level_for(6.51) == "hard"

    # Cold start.
    level, score, rationale = resolve_level([])
    assert (level, score) == ("medium", None) and rationale

    # Hysteresis, upward: sitting just over the boundary is not promotion.
    level, score, _ = resolve_level([6.5, 6.7], current="medium")
    assert 6.5 < score <= 6.75
    assert level == "medium", "should hold rather than flip on a boundary graze"

    # Clearly over it, and the level moves.
    assert resolve_level([7.0, 7.5], current="medium")[0] == "hard"

    # Hysteresis, downward. Pins a real bug: the margin must apply to the
    # boundary being crossed (5.0), not to a property of the current level. With
    # the medium ceiling used here instead, every demotion sailed through.
    level, score, _ = resolve_level([4.9, 4.9], current="medium")
    assert 4.75 < score < 5.0
    assert level == "medium", "a demotion needs the same margin as a promotion"
    assert resolve_level([4.5, 4.5], current="medium")[0] == "easy"

    # An unresolved severe weakness holds back a promotion...
    held, _, why = resolve_level([7.0, 7.5], current="medium", top_severity=0.8)
    assert held == "medium" and "weakness" in why
    assert resolve_level([7.0, 7.5], current="medium", top_severity=0.2)[0] == "hard"

    # ...but never blocks a demotion. Someone struggling must not be kept on
    # hard content because they are also struggling.
    assert resolve_level([4.0, 4.0], current="medium", top_severity=0.9)[0] == "easy"


def run() -> None:
    check_scoring()

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

        client.post(
            "/v1/onboarding",
            headers=h,
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
