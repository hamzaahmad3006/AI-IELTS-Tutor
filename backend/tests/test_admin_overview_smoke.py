"""Smoke test: admin overview KPIs + the versioned prompt registry."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_admin_overview.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from ai.prompts import all_templates, build, get  # noqa: E402
from core.config import get_settings  # noqa: E402
from main import app  # noqa: E402

ESSAY = "Technology has reshaped how societies learn and communicate. " * 8


def check_registry() -> None:
    templates = {t.id: t for t in all_templates()}
    assert "writing.score" in templates
    assert "speaking.score" in templates

    for template in templates.values():
        assert template.version, template.id
        assert template.description, template.id
        # `label` is what gets shown and logged, so it must identify both.
        assert template.label == f"{template.id}@{template.version}"

    # An unknown id fails loudly rather than silently scoring with nothing.
    try:
        get("nope.score")
    except KeyError:
        pass
    else:  # pragma: no cover
        raise AssertionError("unknown prompt id should raise")

    # build() hands back the template alongside the messages, so a caller
    # cannot record a version it did not actually use.
    messages, template = build(
        "writing.score", essay="x", task_type=2, weakness_summary=""
    )
    assert messages and messages[0].get("role") == "system"
    assert template.id == "writing.score"


def run() -> None:
    check_registry()

    with TestClient(app) as client:
        # A learner generates the activity the KPIs count.
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Kpi Learner",
                "email": "kpi@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "kpi@example.com", "password": "StrongPass123"},
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
        client.post(
            "/v1/writing/attempts",
            headers=h,
            json={"essayText": ESSAY, "taskType": 2},
        )

        # A learner must not be able to read platform-wide figures.
        assert client.get("/v1/admin/overview", headers=h).status_code == 403
        assert client.get("/v1/admin/overview").status_code in (401, 403)

        settings = get_settings()
        admin_login = client.post(
            "/v1/auth/login",
            json={
                "email": settings.seed_admin_email,
                "password": settings.seed_admin_password,
            },
        )
        assert admin_login.status_code == 200, admin_login.text
        admin = {
            "Authorization": f"Bearer {admin_login.json()['tokens']['accessToken']}"
        }

        r = client.get("/v1/admin/overview", headers=admin)
        assert r.status_code == 200, r.text
        d = r.json()

        # Counts reflect real rows, not estimates.
        assert d["totalUsers"] >= 2, d
        assert d["onboardedUsers"] >= 1, d
        assert d["activeLearnersLastWeek"] >= 1, d
        assert d["totalAttempts"] >= 1, d
        assert {m["module"] for m in d["attemptsByModule"]} == {
            "writing",
            "speaking",
            "reading",
            "listening",
        }
        assert sum(m["attempts"] for m in d["attemptsByModule"]) == d["totalAttempts"]

        # The AI call just made is counted, with its cost and tokens.
        assert d["aiCalls"] >= 1, d
        assert d["aiTokens"] > 0, d
        assert d["aiFailures"] == 0, d

        # Live prompt versions are reported, so a scoring change can be dated.
        prompts = {p["id"]: p["version"] for p in d["prompts"]}
        assert "writing.score" in prompts and "speaking.score" in prompts
        assert all(prompts.values())

        assert d["generatedAt"]

    print("ADMIN OVERVIEW SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
