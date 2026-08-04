"""Smoke test: full mock test assembly, scoring and readiness verdict."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_mock_test.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from controllers.mock_test_controller import SECTION_MINUTES, _readiness  # noqa: E402
from main import app  # noqa: E402

ESSAY = "Technology has reshaped how societies learn and communicate. " * 8


def check_readiness() -> None:
    # A strong average hiding a weak section must not read as "Ready": most
    # institutions set a per-band minimum as well as an overall.
    lopsided = _readiness(
        {"reading": 9.0, "listening": 9.0, "writing": 5.0, "speaking": 5.0},
        7.0,
        7.0,
    )
    assert lopsided.overall_band == 7.0
    assert lopsided.verdict != "Ready", lopsided.verdict
    assert lopsided.weakest_module in {"writing", "speaking"}
    assert "below target on its own" in lopsided.headline, lopsided.headline

    # Genuinely even and at target.
    even = _readiness(
        {"reading": 7.0, "listening": 7.0, "writing": 7.0, "speaking": 7.0},
        7.0,
        7.0,
    )
    assert even.verdict == "Ready", even.verdict
    assert "hold this level" in even.advice

    # Half a band short everywhere.
    near = _readiness(
        {"reading": 6.5, "listening": 6.5, "writing": 6.5, "speaking": 6.5},
        6.5,
        7.0,
    )
    assert near.verdict == "Nearly ready", near.verdict

    # Nothing submitted at all.
    empty = _readiness(
        {"reading": None, "listening": None, "writing": None, "speaking": None},
        None,
        7.0,
    )
    assert empty.verdict == "Not measured"
    assert empty.weakest_module is None
    assert all(m.band is None for m in empty.modules)


def run() -> None:
    check_readiness()

    with TestClient(app) as client:
        assert client.post("/v1/mock-tests").status_code in (401, 403)

        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Mock Sitter",
                "email": "mock@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "mock@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}
        client.post(
            "/v1/onboarding",
            headers=h,
            json={
                "examType": "academic",
                "selfLevel": "intermediate",
                "targetBand": 7.0,
                "examDate": None,
                "dailyMinutes": 30,
                "consentVoice": False,
                "consentAi": True,
            },
        )

        r = client.post("/v1/mock-tests", headers=h)
        assert r.status_code == 201, r.text
        test = r.json()
        assert test["status"] == "in_progress"
        assert [s["module"] for s in test["sections"]] == [
            "listening",
            "reading",
            "writing",
            "speaking",
        ]
        assert test["totalMinutes"] == sum(SECTION_MINUTES.values())
        # Content is fixed at start so a resumed sitting serves the same items.
        assert test["passageId"] and test["clipId"]
        assert test["writingPromptId"] and test["cueCardId"]

        # Reveal the reading key, then sit the test.
        probe = client.post(
            "/v1/reading/attempts",
            headers=h,
            json={"passageId": test["passageId"], "answers": {}},
        ).json()
        key = {pq["questionId"]: pq["correctAnswer"] for pq in probe["perQuestion"]}

        writing_before = len(
            client.get("/v1/writing/history", headers=h).json()["items"]
        )

        result = client.post(
            f"/v1/mock-tests/{test['id']}/submit",
            headers=h,
            json={"readingAnswers": key, "writingText": ESSAY},
        )
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["status"] == "completed"
        assert body["overallBand"] is not None

        readiness = body["readiness"]
        assert readiness["targetBand"] == 7.0
        assert {m["module"] for m in readiness["modules"]} == {
            "reading",
            "listening",
            "writing",
            "speaking",
        }
        # Sections that were not sat are named, because an overall built from
        # two sections is not comparable to one built from four.
        assert "2 of 4 sections" in readiness["advice"], readiness["advice"]
        for module in readiness["modules"]:
            if module["band"] is None:
                assert module["verdict"] == "Not attempted"

        # Sections go through the real module controllers, so the attempt shows
        # up in history rather than being graded in a parallel implementation.
        writing_after = len(
            client.get("/v1/writing/history", headers=h).json()["items"]
        )
        assert writing_after == writing_before + 1

        # A completed test cannot be resubmitted.
        again = client.post(
            f"/v1/mock-tests/{test['id']}/submit",
            headers=h,
            json={"readingAnswers": key},
        )
        assert again.status_code == 409, again.text

        history = client.get("/v1/mock-tests", headers=h).json()
        assert len(history) == 1
        assert history[0]["id"] == test["id"]

        # Another learner cannot submit someone else's sitting.
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Other Sitter",
                "email": "mock-other@example.com",
                "password": "StrongPass123",
            },
        )
        other_login = client.post(
            "/v1/auth/login",
            json={"email": "mock-other@example.com", "password": "StrongPass123"},
        ).json()
        other = {
            "Authorization": f"Bearer {other_login['tokens']['accessToken']}"
        }
        stolen = client.post(
            f"/v1/mock-tests/{test['id']}/submit", headers=other, json={}
        )
        assert stolen.status_code == 404, stolen.text

    print("MOCK TEST SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
