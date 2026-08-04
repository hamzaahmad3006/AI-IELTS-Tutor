"""Smoke test: /analytics/insights + the streak helpers it relies on."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import date, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_insights.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from controllers.dashboard_controller import _longest_streak, _streak  # noqa: E402
from main import app  # noqa: E402

MODULES = {"speaking", "writing", "reading", "listening"}


def check_streaks() -> None:
    today = date.today()

    assert _streak(set()) == 0
    assert _longest_streak(set()) == 0

    # A run ending today.
    run = {today - timedelta(days=i) for i in range(4)}
    assert _streak(run) == 4

    # A run ending yesterday still counts: a streak is only lost after a full
    # missed day, otherwise a 30-day run would read 0 at 00:01.
    ending_yesterday = {today - timedelta(days=i) for i in range(1, 5)}
    assert _streak(ending_yesterday) == 4

    # Two days ago is genuinely broken.
    stale = {today - timedelta(days=i) for i in range(2, 6)}
    assert _streak(stale) == 0

    # Longest looks at all history, not just the current run.
    history = (
        {today - timedelta(days=i) for i in range(0, 2)}      # 2-day run now
        | {today - timedelta(days=i) for i in range(10, 16)}  # 6-day run before
    )
    assert _streak(history) == 2
    assert _longest_streak(history) == 6


def _reading_attempt(client: TestClient, headers: dict[str, str]) -> None:
    passage = client.get("/v1/reading/passages", headers=headers).json()
    client.post(
        "/v1/reading/attempts",
        headers=headers,
        json={
            "passageId": passage["id"],
            "answers": {q["id"]: "__wrong__" for q in passage["questions"]},
        },
    )


def run() -> None:
    check_streaks()

    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Ines Duarte",
                "email": "insights@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "insights@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        assert client.get("/v1/analytics/insights").status_code in (401, 403)

        # Fresh account: no strengths invented, and the copy says so.
        r = client.get("/v1/analytics/insights", headers=h)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["strengths"] == []
        assert d["weaknesses"] == []
        assert "Complete a practice" in d["summary"], d["summary"]

        c = d["consistency"]
        assert c["currentStreak"] == 0
        assert c["longestStreak"] == 0
        assert c["totalAttempts"] == 0
        # Time is never invented for modules that do not record it.
        assert c["measuredSpeakingMinutes"] is None
        assert len(c["weeks"]) == 8, c["weeks"]

        # The histogram is ordered oldest first and covers whole weeks.
        starts = [w["weekStart"] for w in c["weeks"]]
        assert starts == sorted(starts)

        # ---- With activity ----
        _reading_attempt(client, h)
        d = client.get("/v1/analytics/insights", headers=h).json()

        assert len(d["strengths"]) >= 1, d["strengths"]
        strength = d["strengths"][0]
        assert strength["module"] in MODULES
        assert 0.0 <= strength["band"] <= 9.0
        assert strength["label"] and strength["detail"]

        # A wrong-answer attempt records weaknesses, which must surface.
        assert len(d["weaknesses"]) >= 1, d["weaknesses"]
        weakness = d["weaknesses"][0]
        assert weakness["tagLabel"] and "_" not in weakness["tagLabel"]
        # Labels are written for prose, not derived blindly from the tag.
        assert weakness["tagLabel"] != weakness["tag"]
        assert weakness["occurrences"] >= 1
        # Worst first.
        severities = [w["severity"] for w in d["weaknesses"]]
        assert severities == sorted(severities, reverse=True), severities

        c = d["consistency"]
        assert c["currentStreak"] == 1
        assert c["longestStreak"] == 1
        assert c["activeDaysLast30"] == 1
        assert c["totalAttempts"] == 1
        assert c["weeks"][-1]["attempts"] == 1, "activity lands in the current week"
        assert c["weeks"][-1]["activeDays"] == 1

        # Two attempts on one day: attempts counts submissions, activeDays
        # counts days. Deduplicating both would silently under-report effort.
        _reading_attempt(client, h)
        c = client.get("/v1/analytics/insights", headers=h).json()["consistency"]
        assert c["weeks"][-1]["attempts"] == 2, c["weeks"][-1]
        assert c["weeks"][-1]["activeDays"] == 1, c["weeks"][-1]
        assert c["totalAttempts"] == 2
        assert "Speaking only" in c["timeNote"]

        assert "Complete a practice" not in d["summary"]

    print("INSIGHTS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
