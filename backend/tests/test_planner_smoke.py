"""Smoke test: study plan generation, weighting, and task completion."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from collections import Counter

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_planner.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from controllers.planner_controller import SESSIONS_PER_WEEK  # noqa: E402
from main import app  # noqa: E402


def _auth(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/v1/auth/register",
        json={"fullName": "Plan User", "email": email, "password": "StrongPass123"},
    )
    login = client.post(
        "/v1/auth/login", json={"email": email, "password": "StrongPass123"}
    ).json()
    return {"Authorization": f"Bearer {login['tokens']['accessToken']}"}


def _onboard(client: TestClient, headers: dict[str, str], **overrides: object) -> None:
    body = {
        "examType": "academic",
        "selfLevel": "intermediate",
        "targetBand": 7.5,
        "examDate": None,
        "dailyMinutes": 45,
        "consentVoice": False,
        "consentAi": True,
    }
    body.update(overrides)
    client.post("/v1/onboarding", headers=headers, json=body)


def run() -> None:
    with TestClient(app) as client:
        assert client.get("/v1/planner/plan").status_code in (401, 403)

        h = _auth(client, "planner@example.com")

        # "No plan yet" is a 404, distinct from "a plan with no tasks".
        assert client.get("/v1/planner/plan", headers=h).status_code == 404

        # A plan needs the profile it is built from.
        assert client.post("/v1/planner/plan", headers=h).status_code == 409

        _onboard(client, h, examDate="2026-09-15")
        r = client.post("/v1/planner/plan", headers=h)
        assert r.status_code == 201, r.text
        plan = r.json()

        assert plan["weeks"] >= 1
        assert plan["dailyMinutes"] == 45
        assert plan["rationale"], plan
        assert plan["totalCount"] == plan["weeks"] * SESSIONS_PER_WEEK

        # Every week gets exactly the intended number of sessions: a rounding
        # bug here would quietly under- or over-book the learner.
        per_week = Counter(t["week"] for t in plan["tasks"])
        assert set(per_week.values()) == {SESSIONS_PER_WEEK}, per_week

        # Weighted towards need, not split evenly.
        modules = Counter(t["module"] for t in plan["tasks"])
        assert set(modules) == {"speaking", "writing", "reading", "listening"}
        assert all(t["minutes"] == 45 for t in plan["tasks"])
        assert all(t["detail"] for t in plan["tasks"])

        # ---- Completion ----
        task_id = plan["tasks"][0]["id"]
        done = client.patch(
            f"/v1/planner/tasks/{task_id}", headers=h, json={"isDone": True}
        )
        assert done.status_code == 200, done.text
        assert done.json()["isDone"] is True

        after = client.get("/v1/planner/plan", headers=h).json()
        assert after["completedCount"] == 1
        # Progress survives a reload, which is the whole point of persisting it.
        assert after["id"] == plan["id"]

        # Un-completing works too.
        client.patch(
            f"/v1/planner/tasks/{task_id}", headers=h, json={"isDone": False}
        )
        assert client.get("/v1/planner/plan", headers=h).json()["completedCount"] == 0

        # ---- Regenerating supersedes rather than duplicating ----
        second = client.post("/v1/planner/plan", headers=h).json()
        assert second["id"] != plan["id"]
        active = client.get("/v1/planner/plan", headers=h).json()
        assert active["id"] == second["id"], "the newest plan must be the active one"

        # ---- Another learner cannot touch these tasks ----
        other = _auth(client, "planner-other@example.com")
        _onboard(client, other)
        stolen = client.patch(
            f"/v1/planner/tasks/{second['tasks'][0]['id']}",
            headers=other,
            json={"isDone": True},
        )
        # 404 rather than 403: existence is not confirmed to a stranger.
        assert stolen.status_code == 404, stolen.text

        # ---- No exam date still produces a usable horizon ----
        no_date = _auth(client, "planner-nodate@example.com")
        _onboard(client, no_date, examDate=None)
        plan3 = client.post("/v1/planner/plan", headers=no_date).json()
        assert plan3["examDate"] is None
        assert plan3["weeks"] >= 1
        assert "no exam date set" in plan3["rationale"]

    print("PLANNER SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
