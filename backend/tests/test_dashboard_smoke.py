"""Smoke test: real Home dashboard overview composed from stored data."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_dashboard.db")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

ESSAY = "Technology has reshaped how societies learn and communicate today. " * 6


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Sarah Ahmed",
                "email": "dash@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "dash@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        # Requires auth
        assert client.get("/v1/analytics/overview").status_code in (401, 403)

        # Onboarding sets the target band for the prediction/coach copy
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

        # Fresh account: overview works, no attempts yet
        r = client.get("/v1/analytics/overview", headers=h)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["greetingName"] == "Sarah"  # first name only
        assert d["streakDays"] == 0
        assert d["prediction"]["basedOnSessions"] == 0
        assert len(d["modules"]) == 4
        assert d["checklistCompletionPct"] == 0

        # Do two practices today -> streak 1, prediction based on 2 sessions
        client.post("/v1/writing/attempts", headers=h, json={"essayText": ESSAY, "taskType": 2})
        passage = client.get("/v1/reading/passages", headers=h).json()
        qids = [q["id"] for q in passage["questions"]]
        client.post(
            "/v1/reading/attempts",
            headers=h,
            json={"passageId": passage["id"], "answers": {qids[0]: "China", qids[1]: "true", qids[2]: "black"}},
        )

        r = client.get("/v1/analytics/overview", headers=h)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["streakDays"] == 1, d
        assert d["prediction"]["basedOnSessions"] == 2
        assert d["prediction"]["predictedBand"] > 0
        # Exactly one module is the active (weakest) tile
        assert sum(1 for m in d["modules"] if m["isActive"]) == 1
        # The high-priority recommendation is completed (practiced today)
        weak_item = next(i for i in d["checklist"] if i["priority"] == "high")
        assert weak_item["isCompleted"] is True
        assert d["checklistCompletionPct"] > 0

    print("DASHBOARD SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
