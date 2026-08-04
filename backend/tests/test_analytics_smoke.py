"""Smoke test: analytics progress + band prediction from real attempts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_analytics.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

ESSAY = "Technology has transformed modern society in profound ways. " * 8
TRANSCRIPT = "I recently visited a wonderful coastal town and truly enjoyed it. " * 5


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Analytics User",
                "email": "analytics@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "analytics@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        # Onboarding sets an exam date -> prediction horizon
        client.post(
            "/v1/onboarding",
            headers=h,
            json={
                "examType": "academic",
                "selfLevel": "intermediate",
                "targetBand": 7.5,
                "examDate": "2026-12-01",
                "dailyMinutes": 60,
                "consentVoice": True,
                "consentAi": True,
            },
        )

        # Generate attempts across all four modules
        client.post("/v1/writing/attempts", headers=h, json={"essayText": ESSAY, "taskType": 2})
        client.post("/v1/speaking/attempts", headers=h, json={"transcript": TRANSCRIPT, "part": 2})

        passage = client.get("/v1/reading/passages", headers=h).json()
        qids = [q["id"] for q in passage["questions"]]
        client.post(
            "/v1/reading/attempts",
            headers=h,
            json={"passageId": passage["id"], "answers": {qids[0]: "China", qids[1]: "true", qids[2]: "black"}},
        )

        clip = client.get("/v1/listening/clips", headers=h).json()
        cqids = [q["id"] for q in clip["questions"]]
        client.post(
            "/v1/listening/attempts",
            headers=h,
            json={
                "audioId": clip["id"],
                "answers": {
                    cqids[0]: "student card",
                    cqids[1]: "Second floor of the science building",
                    cqids[2]: "ten",
                },
            },
        )

        # Progress
        r = client.get("/v1/analytics/progress", headers=h)
        assert r.status_code == 200, r.text
        prog = r.json()
        assert prog["totalAttempts"] == 4, prog
        assert prog["overallBand"] is not None
        by_module = {m["module"]: m for m in prog["modules"]}
        for module in ("speaking", "writing", "reading", "listening"):
            assert by_module[module]["attempts"] == 1
            assert by_module[module]["currentBand"] is not None

        # Prediction
        r = client.get("/v1/analytics/prediction", headers=h)
        assert r.status_code == 200, r.text
        pred = r.json()
        assert pred["horizonDate"] == "2026-12-01"
        assert 0 <= pred["confidence"] <= 0.95
        overall = pred["predictedOverall"]
        assert overall is not None and 0 <= overall <= 9 and (overall * 2) % 1 == 0
        for module in ("speaking", "writing", "reading", "listening"):
            assert pred["modules"][module] is not None

    print("ANALYTICS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
