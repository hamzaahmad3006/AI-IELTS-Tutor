"""Smoke test: placement diagnostic + the CEFR mapping it reports."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_diagnostic.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from core.cefr import band_to_cefr  # noqa: E402
from main import app  # noqa: E402

LONG_ESSAY = (
    "Technology has reshaped how people learn and communicate across the world. "
) * 5
LONG_SPOKEN = (
    "I enjoy spending time in the public library near my home because it is quiet. "
) * 3


def check_cefr() -> None:
    assert band_to_cefr(None) is None
    assert band_to_cefr(9.0) == "C2"
    assert band_to_cefr(8.5) == "C2"
    assert band_to_cefr(8.0) == "C1"
    assert band_to_cefr(7.0) == "C1"
    assert band_to_cefr(6.5) == "B2"
    assert band_to_cefr(5.5) == "B2"
    assert band_to_cefr(5.0) == "B1"
    assert band_to_cefr(4.0) == "B1"
    assert band_to_cefr(3.0) == "A2"
    # Below the published alignment, but a level still has to be reported.
    assert band_to_cefr(1.0) == "A1"


def _auth(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/v1/auth/register",
        json={"fullName": "Placement User", "email": email, "password": "StrongPass123"},
    )
    login = client.post(
        "/v1/auth/login", json={"email": email, "password": "StrongPass123"}
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
            "consentVoice": False,
            "consentAi": True,
        },
    )
    return headers


def run() -> None:
    check_cefr()

    with TestClient(app) as client:
        assert client.get("/v1/diagnostic").status_code in (401, 403)

        h = _auth(client, "diagnostic@example.com")

        # The set assembles even on a fresh database: the content banks seed
        # lazily from their own endpoints, which the diagnostic never hits.
        r = client.get("/v1/diagnostic", headers=h)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["reading"]["questions"], d
        assert d["listening"]["questions"], d
        assert d["listening"]["audioUrl"].startswith("/media/")
        assert d["writing"]["prompt"] and d["speaking"]["prompt"]
        # Answers must never leak in the question set.
        for section in ("reading", "listening"):
            for question in d[section]["questions"]:
                assert "correctAnswer" not in question

        # ---- Full marks on reading, everything else skipped ----
        wrong = {q["id"]: "__wrong__" for q in d["reading"]["questions"]}
        first = client.post(
            "/v1/diagnostic", headers=h, json={"readingAnswers": wrong}
        )
        assert first.status_code == 200, first.text
        result = first.json()

        by_module = {b["module"]: b for b in result["baselines"]}
        assert set(by_module) == {"reading", "writing", "speaking", "listening"}

        # Skipped modules are null, not zero: a fabricated starting band would
        # poison every prediction built on top of it.
        assert by_module["listening"]["band"] is None
        assert by_module["writing"]["band"] is None
        assert by_module["speaking"]["band"] is None
        assert "Not attempted" in by_module["listening"]["detail"]
        assert "excluded rather than guessed" in result["summary"], result["summary"]

        # ---- A response too short to judge is not scored ----
        second = client.post(
            "/v1/diagnostic",
            headers=h,
            json={"readingAnswers": wrong, "speakingText": "Short."},
        ).json()
        speaking = {b["module"]: b for b in second["baselines"]}["speaking"]
        assert speaking["band"] is None
        assert "Too short" in speaking["detail"], speaking

        # ---- A full attempt produces bands and writes the profile ----
        third = client.post(
            "/v1/diagnostic",
            headers=h,
            json={
                "readingAnswers": wrong,
                "listeningAnswers": {},
                "writingText": LONG_ESSAY,
                "speakingText": LONG_SPOKEN,
            },
        ).json()
        scored = {b["module"]: b for b in third["baselines"]}
        assert scored["writing"]["band"] is not None
        assert scored["speaking"]["band"] is not None
        assert third["overallBand"] is not None
        assert third["cefrLevel"] == band_to_cefr(third["overallBand"])
        assert third["cefrDescription"]

        profile = client.get("/v1/profile", headers=h).json()
        assert profile["cefrLevel"] == third["cefrLevel"]
        assert profile["baselines"]["writing"] == scored["writing"]["band"]
        assert profile["baselines"]["reading"] == scored["reading"]["band"]

        # ---- Nothing submitted at all ----
        empty = client.post("/v1/diagnostic", headers=h, json={}).json()
        assert empty["overallBand"] is None
        assert empty["cefrLevel"] is None
        assert all(b["band"] is None for b in empty["baselines"])

    print("DIAGNOSTIC SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
