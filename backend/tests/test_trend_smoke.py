"""Smoke test: /analytics/trend band series per module + running overall."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_trend.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

MODULES = {"speaking", "writing", "reading", "listening"}


#: `_reading_band` submits twice - a probe to reveal the key, then the key
#: itself - and both are real attempts, so each call adds two trend points.
POINTS_PER_CALL = 2


def _reading_band(client: TestClient, headers: dict[str, str]) -> float:
    """Complete one reading passage with full marks and return its band.

    Creates `POINTS_PER_CALL` attempts, not one: the answer key is not exposed
    by the API, so it has to be revealed by a deliberately wrong submission
    first, and that submission is itself a scored attempt.
    """
    passage = client.get("/v1/reading/passages", headers=headers).json()

    # Passages are served at random, so the key is derived from a deliberately
    # wrong submission rather than hard-coded.
    wrong = {q["id"]: "__definitely_wrong__" for q in passage["questions"]}
    revealed = client.post(
        "/v1/reading/attempts",
        headers=headers,
        json={"passageId": passage["id"], "answers": wrong},
    ).json()
    key = {
        pq["questionId"]: pq["correctAnswer"] for pq in revealed["perQuestion"]
    }
    scored = client.post(
        "/v1/reading/attempts",
        headers=headers,
        json={"passageId": passage["id"], "answers": key},
    ).json()
    return float(scored["band"])


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Trend User",
                "email": "trend@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "trend@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        # Requires auth
        assert client.get("/v1/analytics/trend").status_code in (401, 403)

        # Fresh account: every module present, all series empty.
        r = client.get("/v1/analytics/trend", headers=h)
        assert r.status_code == 200, r.text
        d = r.json()
        assert {m["module"] for m in d["modules"]} == MODULES
        assert all(m["points"] == [] for m in d["modules"])
        assert d["overall"] == []

        # Reading attempts land on the reading series only.
        band = _reading_band(client, h)
        d = client.get("/v1/analytics/trend", headers=h).json()
        by_module = {m["module"]: m["points"] for m in d["modules"]}
        reading = by_module["reading"]
        assert len(reading) == POINTS_PER_CALL, reading
        assert reading[-1]["band"] == band  # last point is the scored attempt
        assert reading[0]["at"]  # timestamp serialised
        assert all(by_module[m] == [] for m in MODULES - {"reading"})

        # With one module scored, the running overall equals that module's band.
        assert len(d["overall"]) == POINTS_PER_CALL
        assert d["overall"][-1]["band"] == band

        # Further attempts append, oldest first.
        _reading_band(client, h)
        d = client.get("/v1/analytics/trend", headers=h).json()
        reading = {m["module"]: m["points"] for m in d["modules"]}["reading"]
        assert len(reading) == 2 * POINTS_PER_CALL, reading
        stamps = [p["at"] for p in reading]
        assert stamps == sorted(stamps), "series must be oldest-first"
        assert len(d["overall"]) == 2 * POINTS_PER_CALL

        # Bands stay inside the IELTS scale.
        for module in d["modules"]:
            for point in module["points"]:
                assert 0.0 <= point["band"] <= 9.0, point

    print("TREND SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
