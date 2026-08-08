"""Smoke test: study time, reported by the client and clamped here.

The clamp is the interesting part. Only the client knows how long someone spent
on a passage, and a backgrounded app, a paused timer that never resumed, or a
phone left on a desk all produce numbers wrong in the same direction.

Clamping is not fraud prevention -- almost no learner is adversarial. It is the
difference between "you studied 40 minutes this week", which is useful, and
"you studied 19 hours", which is obviously broken and makes every other figure
on the screen suspect.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_time_on_task.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from core.time_on_task import (  # noqa: E402
    CEILINGS,
    MIN_SECONDS,
    clamp,
    total_minutes,
)
from main import app  # noqa: E402

PASSWORD = "StrongPass123"
ESSAY = "Urbanisation has reshaped how populations live and work worldwide. " * 6


def check_clamping() -> None:
    # An ordinary duration passes through untouched.
    assert clamp(600, "writing") == 600

    # A forgotten timer does not. The ceiling is set from what the real exam
    # allows plus slack, not from what someone could sit through.
    assert clamp(19 * 3600, "writing") == CEILINGS["writing"]
    assert clamp(10 * 3600, "reading") == CEILINGS["reading"]
    assert clamp(10 * 3600, "listening") == CEILINGS["listening"]

    # Ceilings differ per module, because the modules do.
    assert CEILINGS["writing"] > CEILINGS["listening"]

    # A tap is not study. Counting it would inflate the total with noise while
    # looking precise.
    assert clamp(MIN_SECONDS - 1, "writing") == 0
    assert clamp(0, "writing") == 0
    assert clamp(None, "writing") == 0

    # An unknown module still gets a ceiling rather than unbounded trust.
    assert clamp(10 * 3600, "unknown") < 10 * 3600


def check_minutes_rounding() -> None:
    assert total_minutes(0) == 0
    assert total_minutes(120) == 2
    # Rounded, not truncated: 59 seconds shown as "0 minutes" reads as the app
    # having lost the work.
    assert total_minutes(59) == 1
    assert total_minutes(89) == 1
    assert total_minutes(91) == 2


def run() -> None:
    check_clamping()
    check_minutes_rounding()

    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Timed Learner",
                "email": "timed@example.com",
                "password": PASSWORD,
            },
        )
        h = {
            "Authorization": "Bearer "
            + client.post(
                "/v1/auth/login",
                json={"email": "timed@example.com", "password": PASSWORD},
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

        before = client.get("/v1/analytics/overview", headers=h)
        assert before.status_code == 200, before.text
        assert before.json()["studyTime"]["totalMinutes"] == 0

        # Twelve minutes of writing.
        r = client.post(
            "/v1/writing/attempts",
            headers=h,
            json={"essayText": ESSAY, "taskType": 2, "durationSec": 720},
        )
        assert r.status_code == 201, r.text

        after = client.get("/v1/analytics/overview", headers=h).json()["studyTime"]
        assert after["totalMinutes"] == 12, after
        assert after["todayMinutes"] == 12
        assert after["weekMinutes"] == 12
        assert after["dailyGoalMinutes"] == 30
        assert after["dailyGoalPct"] == 40, after

        # A forgotten timer is clamped rather than believed.
        r = client.post(
            "/v1/writing/attempts",
            headers=h,
            json={"essayText": ESSAY, "taskType": 2, "durationSec": 19 * 3600},
        )
        assert r.status_code == 201, r.text

        capped = client.get("/v1/analytics/overview", headers=h).json()["studyTime"]
        # 12 minutes plus the 90-minute ceiling, not 12 plus nineteen hours.
        assert capped["totalMinutes"] == 12 + 90, capped

        # The goal percentage is capped, because "340% of your goal" reads as a
        # warning rather than praise.
        assert capped["dailyGoalPct"] == 100, capped

        # A submission with no duration is still a valid submission: the client
        # may be an older build, and refusing it would break the app to collect
        # a statistic.
        r = client.post(
            "/v1/writing/attempts",
            headers=h,
            json={"essayText": ESSAY, "taskType": 2},
        )
        assert r.status_code == 201, r.text
        assert (
            client.get("/v1/analytics/overview", headers=h).json()["studyTime"][
                "totalMinutes"
            ]
            == 102
        )

        # A negative duration is refused outright: it is not an imprecise
        # measurement, it is a broken client.
        bad = client.post(
            "/v1/writing/attempts",
            headers=h,
            json={"essayText": ESSAY, "taskType": 2, "durationSec": -60},
        )
        assert bad.status_code in (400, 422), bad.text

    print("TIME ON TASK SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
