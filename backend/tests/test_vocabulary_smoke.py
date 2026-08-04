"""Smoke test: vocabulary SRS queue, grading and scheduling."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_vocab.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from core.srs import ScheduleState, next_state  # noqa: E402
from main import app  # noqa: E402


def check_algorithm() -> None:
    """SM-2 behaviour that the schedule depends on."""
    fresh = ScheduleState(repetitions=0, interval_days=0, ease_factor=2.5)

    # First two successful recalls use the fixed 1-day then 6-day steps.
    first = next_state(fresh, 5)
    assert (first.repetitions, first.interval_days) == (1, 1), first
    second = next_state(first, 5)
    assert (second.repetitions, second.interval_days) == (2, 6), second

    # From the third repetition the interval grows by the ease factor.
    third = next_state(second, 5)
    assert third.repetitions == 3
    assert third.interval_days == round(6 * second.ease_factor), third

    # A failed recall resets the streak and brings the card back tomorrow.
    lapsed = next_state(third, 1)
    assert lapsed.repetitions == 0, lapsed
    assert lapsed.interval_days == 1, lapsed
    assert lapsed.ease_factor < third.ease_factor, "ease should drop on a lapse"

    # Ease never falls below the SM-2 floor, even after repeated failures.
    state = fresh
    for _ in range(20):
        state = next_state(state, 0)
    assert state.ease_factor >= 1.3, state

    # A hard-but-correct recall (3) should not raise the ease factor.
    hard = next_state(fresh, 3)
    assert hard.ease_factor <= fresh.ease_factor, hard

    # Grades outside 0-5 are rejected.
    for bad in (-1, 6):
        try:
            next_state(fresh, bad)
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"grade {bad} should be rejected")


def run() -> None:
    check_algorithm()

    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Vocab User",
                "email": "vocab@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "vocab@example.com", "password": "StrongPass123"},
        ).json()
        headers = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        # Requires auth.
        assert client.get("/v1/vocabulary/review").status_code in (401, 403)

        # A fresh learner gets only new cards.
        r = client.get("/v1/vocabulary/review?limit=5", headers=headers)
        assert r.status_code == 200, r.text
        queue = r.json()
        assert len(queue["items"]) == 5, queue
        assert queue["dueCount"] == 0
        assert queue["newCount"] == 5
        for card in queue["items"]:
            assert card["word"] and card["definition"]
            assert card["isNew"] is True

        first_item = queue["items"][0]["itemId"]

        # Stats before any review.
        stats = client.get("/v1/vocabulary/stats", headers=headers).json()
        assert stats["totalItems"] >= 8, stats
        assert stats["started"] == 0
        assert stats["dueNow"] == 0

        # Grade a card well -> scheduled 1 day out, so not due now.
        r = client.post(
            "/v1/vocabulary/grade",
            headers=headers,
            json={"itemId": first_item, "grade": 5},
        )
        assert r.status_code == 200, r.text
        graded = r.json()
        assert graded["repetitions"] == 1
        assert graded["intervalDays"] == 1
        assert graded["totalReviews"] == 1

        # It is now "started" but not due.
        stats = client.get("/v1/vocabulary/stats", headers=headers).json()
        assert stats["started"] == 1, stats
        assert stats["dueNow"] == 0, stats

        # It should not reappear in the queue while it is not due.
        queue = client.get("/v1/vocabulary/review?limit=10", headers=headers).json()
        assert all(card["itemId"] != first_item for card in queue["items"]), queue

        # Grading the same card again advances the schedule (no duplicate row).
        r = client.post(
            "/v1/vocabulary/grade",
            headers=headers,
            json={"itemId": first_item, "grade": 4},
        )
        assert r.json()["repetitions"] == 2
        assert r.json()["totalReviews"] == 2
        assert client.get("/v1/vocabulary/stats", headers=headers).json()["started"] == 1

        # Invalid grade is rejected.
        assert (
            client.post(
                "/v1/vocabulary/grade",
                headers=headers,
                json={"itemId": first_item, "grade": 9},
            ).status_code
            == 422
        )

        # Unknown item is a clean 404.
        assert (
            client.post(
                "/v1/vocabulary/grade",
                headers=headers,
                json={"itemId": "does-not-exist", "grade": 4},
            ).status_code
            == 404
        )

    print("VOCABULARY SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
